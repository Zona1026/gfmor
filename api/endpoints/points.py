from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from api.dependencies.admin_auth import require_self_or_admin
from db import models
from db.database import get_db
from db.points import expire_points, get_user_point_summary
from schemas.points import PointHistoryItem, PointHistoryRecord, PointSummary

router = APIRouter()


@router.get("/user/{google_id}/summary", response_model=PointSummary, summary="查詢會員點數摘要")
def read_user_point_summary(
    google_id: str,
    auth=Depends(require_self_or_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.google_id == google_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到該會員")

    summary = get_user_point_summary(db, google_id)
    db.commit()
    return summary


def _point_history_items(transaction):
    if transaction.work_order:
        return [
            PointHistoryItem(
                id=f"work-order-item-{item.id}",
                name=item.name,
                quantity=item.quantity or 1,
            )
            for item in transaction.work_order.line_items
            if item.counts_toward_membership
        ]

    if transaction.order:
        return [
            PointHistoryItem(
                id=f"order-item-{item.id}",
                name=item.product.name if item.product else f"商品 #{item.product_id}",
                quantity=item.quantity or 1,
            )
            for item in transaction.order.items
        ]

    return []


def _point_source(transaction):
    if transaction.work_order_id:
        return "work_order", transaction.work_order_id, f"工單 #{transaction.work_order_id}"
    if transaction.order_id:
        return "order", transaction.order_id, f"商城訂單 #{transaction.order_id}"
    return "points", None, "點數調整"


@router.get(
    "/user/{google_id}/transactions",
    response_model=List[PointHistoryRecord],
    summary="查詢會員點數累積與使用紀錄",
)
def read_user_point_transactions(
    google_id: str,
    limit: int = Query(200, ge=1, le=500),
    auth=Depends(require_self_or_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.google_id == google_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到該會員")

    expire_points(db, google_id=google_id)
    db.flush()
    transactions = (
        db.query(models.PointTransaction)
        .options(
            joinedload(models.PointTransaction.order)
            .joinedload(models.Order.items)
            .joinedload(models.OrderItem.product),
            joinedload(models.PointTransaction.work_order)
            .joinedload(models.WorkOrder.line_items),
        )
        .filter(models.PointTransaction.google_id == google_id)
        .order_by(
            models.PointTransaction.issued_at.desc(),
            models.PointTransaction.id.desc(),
        )
        .limit(limit)
        .all()
    )

    records = []
    for transaction in transactions:
        source_type, source_id, source_label = _point_source(transaction)
        records.append(PointHistoryRecord(
            id=transaction.id,
            type=transaction.type,
            points=transaction.points,
            source_type=source_type,
            source_id=source_id,
            source_label=source_label,
            items=_point_history_items(transaction),
            issued_at=transaction.issued_at,
            expires_at=transaction.expires_at,
            note=transaction.note,
        ))

    db.commit()
    return records
