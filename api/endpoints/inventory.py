from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from api.dependencies.admin_auth import require_admin, require_super_admin
from db import inventory as inventory_service
from db import models
from db.database import get_db
from schemas import inventory as inventory_schema

router = APIRouter()


def _product_payload(db: Session, product, can_view_detail: bool):
    reserved = inventory_service.reserved_quantity(db, product.id)
    available = max(0, (product.stock or 0) - reserved)
    payload = {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "category_info": product.category_info,
        "inventory_type": product.inventory_type,
        "low_stock_threshold": product.low_stock_threshold or 5,
        "available_stock": available,
        "is_low_stock": available <= (product.low_stock_threshold or 5),
    }
    if can_view_detail:
        payload["stock"] = product.stock or 0
        payload["reserved_stock"] = reserved
    return payload


@router.get("/items", response_model=List[inventory_schema.InventoryProduct])
def read_inventory_items(
    type: str = Query("all"),
    low_stock: bool = False,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    query = db.query(models.Product).options(joinedload(models.Product.category_info))
    if type == "shop":
        query = query.filter(models.Product.inventory_type.in_([
            models.InventoryType.SHOP,
            models.InventoryType.BOTH,
        ]))
    elif type == "part":
        query = query.filter(models.Product.inventory_type.in_([
            models.InventoryType.PART,
            models.InventoryType.BOTH,
        ]))
    elif type != "all":
        raise HTTPException(status_code=400, detail="type must be shop, part, or all")

    items = [
        _product_payload(db, product, admin["is_manager"])
        for product in query.order_by(models.Product.id.asc()).all()
    ]
    if low_stock:
        items = [item for item in items if item["is_low_stock"]]
    return items


@router.get("/movements", response_model=List[inventory_schema.InventoryMovement])
def read_inventory_movements(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    movements = (
        db.query(models.InventoryMovement)
        .options(joinedload(models.InventoryMovement.product))
        .order_by(models.InventoryMovement.created_at.desc(), models.InventoryMovement.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": movement.id,
            "product_id": movement.product_id,
            "product_name": movement.product.name if movement.product else None,
            "movement_type": movement.movement_type,
            "quantity_delta": movement.quantity_delta,
            "stock_before": movement.stock_before,
            "stock_after": movement.stock_after,
            "source_type": movement.source_type,
            "source_id": movement.source_id,
            "actor": movement.actor,
            "reason": movement.reason,
            "created_at": movement.created_at,
        }
        for movement in movements
    ]


@router.get("/reservations", response_model=List[inventory_schema.InventoryReservation])
def read_inventory_reservations(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    query = (
        db.query(models.InventoryReservation)
        .options(joinedload(models.InventoryReservation.product))
    )
    if status_filter:
        try:
            query = query.filter(models.InventoryReservation.status == models.InventoryReservationStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid reservation status")

    reservations = (
        query
        .order_by(models.InventoryReservation.created_at.desc(), models.InventoryReservation.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": reservation.id,
            "product_id": reservation.product_id,
            "product_name": reservation.product.name if reservation.product else None,
            "quantity": reservation.quantity,
            "status": reservation.status,
            "source_type": reservation.source_type,
            "source_id": reservation.source_id,
            "actor": reservation.actor,
            "reason": reservation.reason,
            "created_at": reservation.created_at,
            "updated_at": reservation.updated_at,
        }
        for reservation in reservations
    ]


@router.post("/reservations/{reservation_id}/release", response_model=inventory_schema.InventoryReservation)
def release_inventory_reservation(
    reservation_id: int,
    release: inventory_schema.InventoryReservationReleaseCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    reservation = (
        db.query(models.InventoryReservation)
        .options(joinedload(models.InventoryReservation.product))
        .filter(models.InventoryReservation.id == reservation_id)
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    if reservation.source_type != inventory_service.SOURCE_WORK_ORDER_LINE_ITEM:
        raise HTTPException(status_code=400, detail="Only work order reservations can be released here.")
    if reservation.status != models.InventoryReservationStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active reservations can be released.")

    line_item = db.query(models.WorkOrderLineItem).get(reservation.source_id)
    if line_item and (line_item.inventory_consumed_quantity or 0) > 0:
        raise HTTPException(status_code=400, detail="Consumed inventory reservations cannot be released.")

    reservation.status = models.InventoryReservationStatus.RELEASED
    reservation.actor = release.actor or admin["username"]
    reservation.reason = release.reason
    if line_item:
        line_item.inventory_reserved_quantity = max(
            0,
            (line_item.inventory_reserved_quantity or 0) - (reservation.quantity or 0),
        )
    db.commit()
    db.refresh(reservation)
    return {
        "id": reservation.id,
        "product_id": reservation.product_id,
        "product_name": reservation.product.name if reservation.product else None,
        "quantity": reservation.quantity,
        "status": reservation.status,
        "source_type": reservation.source_type,
        "source_id": reservation.source_id,
        "actor": reservation.actor,
        "reason": reservation.reason,
        "created_at": reservation.created_at,
        "updated_at": reservation.updated_at,
    }


@router.post("/adjustments", response_model=inventory_schema.InventoryProduct, status_code=status.HTTP_201_CREATED)
def create_inventory_adjustment(
    adjustment: inventory_schema.InventoryAdjustmentCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    product = db.query(models.Product).get(adjustment.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    try:
        inventory_service.manual_adjust_inventory(
            db,
            product,
            adjustment.stock_after,
            actor=adjustment.actor or admin["username"],
            reason=adjustment.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(product)
    return _product_payload(db, product, True)


@router.post("/scrap", response_model=inventory_schema.InventoryProduct, status_code=status.HTTP_201_CREATED)
def create_inventory_scrap(
    scrap: inventory_schema.InventoryScrapCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    product = db.query(models.Product).get(scrap.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    try:
        inventory_service.scrap_inventory(
            db,
            product,
            scrap.quantity,
            actor=scrap.actor or admin["username"],
            reason=scrap.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db.commit()
    db.refresh(product)
    return _product_payload(db, product, True)
