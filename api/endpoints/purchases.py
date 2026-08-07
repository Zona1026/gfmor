from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies.admin_auth import require_admin, require_manager_admin, require_super_admin
from db import models
from db import purchases as purchase_service
from db.database import get_db
from schemas import purchase as purchase_schema

router = APIRouter()


def _request_or_404(db: Session, purchase_request_id: int):
    request = purchase_service.get_purchase_request(db, purchase_request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Purchase request not found.")
    return request


@router.get("/", response_model=List[purchase_schema.PurchaseRequest])
def read_purchase_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return purchase_service.get_purchase_requests(db, status=status_filter, skip=skip, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{purchase_request_id}", response_model=purchase_schema.PurchaseRequest)
def read_purchase_request(
    purchase_request_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _request_or_404(db, purchase_request_id)


@router.post("/{purchase_request_id}/order", response_model=purchase_schema.PurchaseRequest)
def order_purchase_request(
    purchase_request_id: int,
    update: purchase_schema.PurchaseOrderUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    request = _request_or_404(db, purchase_request_id)
    try:
        purchase_service.order_purchase_request(db, request, update)
        db.commit()
        return purchase_service.get_purchase_request(db, purchase_request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{purchase_request_id}/receive", response_model=purchase_schema.PurchaseRequest)
def receive_purchase_request(
    purchase_request_id: int,
    receipt: purchase_schema.PurchaseReceiveCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    request = _request_or_404(db, purchase_request_id)
    if not receipt.actor:
        receipt.actor = admin["username"]
    try:
        purchase_service.receive_purchase_request(db, request, receipt)
        db.commit()
        return purchase_service.get_purchase_request(db, purchase_request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{purchase_request_id}/assign", response_model=purchase_schema.PurchaseRequest)
def assign_purchase_request(
    purchase_request_id: int,
    assignment: purchase_schema.PurchaseAssignCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_manager_admin),
):
    request = _request_or_404(db, purchase_request_id)
    work_order = db.query(models.WorkOrder).filter(models.WorkOrder.id == assignment.work_order_id).first()
    if not work_order:
        raise HTTPException(status_code=404, detail="Target work order not found.")
    line_item = (
        db.query(models.WorkOrderLineItem)
        .filter(
            models.WorkOrderLineItem.id == assignment.work_order_line_item_id,
            models.WorkOrderLineItem.work_order_id == assignment.work_order_id,
        )
        .first()
    )
    if not line_item:
        raise HTTPException(status_code=404, detail="Target work order line item not found.")

    quantity = assignment.quantity or request.unassigned_arrived_quantity
    try:
        purchase_service.assign_arrived_quantity(
            db,
            request,
            work_order,
            line_item,
            quantity,
            actor=assignment.actor or admin["username"],
            note=assignment.note,
        )
        db.commit()
        return purchase_service.get_purchase_request(db, purchase_request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{purchase_request_id}/cancel", response_model=purchase_schema.PurchaseRequest)
def cancel_purchase_request(
    purchase_request_id: int,
    cancel: purchase_schema.PurchaseCancelCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    request = _request_or_404(db, purchase_request_id)
    try:
        purchase_service.cancel_purchase_request(db, request, cancel)
        db.commit()
        return purchase_service.get_purchase_request(db, purchase_request_id)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
