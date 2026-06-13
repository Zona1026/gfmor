from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from db import models
from db.database import get_db
from schemas import guest_customer as guest_schema
from schemas import order as order_schema

router = APIRouter()


@router.get("/", response_model=List[guest_schema.GuestCustomer], summary="取得散客列表")
def get_guest_customers(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.GuestCustomer)
    if q:
        keyword = f"%{q}%"
        query = query.filter(
            or_(
                models.GuestCustomer.name.ilike(keyword),
                models.GuestCustomer.phone.ilike(keyword),
            )
        )
    return query.order_by(models.GuestCustomer.updated_at.desc()).limit(200).all()


@router.post("/", response_model=guest_schema.GuestCustomer, summary="建立散客資料")
def create_guest_customer(guest: guest_schema.GuestCustomerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.GuestCustomer).filter(models.GuestCustomer.phone == guest.phone).first()
    if existing:
        existing.name = guest.name
        if guest.notes is not None:
            existing.notes = guest.notes
        db.commit()
        db.refresh(existing)
        return existing

    db_guest = models.GuestCustomer(**guest.dict())
    db.add(db_guest)
    db.commit()
    db.refresh(db_guest)
    return db_guest


@router.get("/{guest_id}", response_model=guest_schema.GuestCustomer, summary="取得單一散客")
def get_guest_customer(guest_id: int, db: Session = Depends(get_db)):
    guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="找不到該散客")
    return guest


@router.get("/{guest_id}/orders", response_model=List[order_schema.Order], summary="取得散客訂單")
def get_guest_orders(guest_id: int, db: Session = Depends(get_db)):
    guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="找不到該散客")

    return (
        db.query(models.Order)
        .options(
            joinedload(models.Order.guest_customer),
            joinedload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .filter(models.Order.guest_customer_id == guest_id)
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.put("/{guest_id}", response_model=guest_schema.GuestCustomer, summary="更新散客資料")
def update_guest_customer(
    guest_id: int,
    update_data: guest_schema.GuestCustomerUpdate,
    db: Session = Depends(get_db),
):
    guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="找不到該散客")

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(guest, key, value)

    db.commit()
    db.refresh(guest)
    return guest


@router.post("/{guest_id}/merge", summary="將散客合併到會員")
def merge_guest_to_member(
    guest_id: int,
    merge_data: guest_schema.GuestCustomerMerge,
    db: Session = Depends(get_db),
):
    guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == guest_id).first()
    if not guest:
        raise HTTPException(status_code=404, detail="找不到該散客")

    user = db.query(models.User).filter(models.User.google_id == merge_data.google_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到目標會員")

    guest_orders = db.query(models.Order).filter(models.Order.guest_customer_id == guest_id).all()
    completed_total = 0
    moved_count = 0

    for order in guest_orders:
        if order.status == models.OrderStatus.COMPLETED:
            completed_total += order.total_amount
        order.google_id = user.google_id
        order.guest_customer_id = None
        moved_count += 1

    if completed_total:
        user.cumulative_consumption = (user.cumulative_consumption or 0) + completed_total

    db.commit()

    return {
        "message": "散客已合併到會員",
        "moved_orders": moved_count,
        "added_consumption": completed_total,
    }
