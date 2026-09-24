from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


def refunded_work_order_amount(db: Session, work_order_id: int) -> int:
    return int(
        db.query(func.coalesce(func.sum(models.RefundRecord.amount), 0))
        .filter(
            models.RefundRecord.source_type == models.AccountingSourceType.WORK_ORDER,
            models.RefundRecord.source_id == work_order_id,
        )
        .scalar()
        or 0
    )


def calculate_work_order_membership_consumption(db: Session, work_order) -> int:
    if (
        not work_order.google_id
        or work_order.deleted_at
        or work_order.status != models.WorkOrderStatus.COMPLETED
        or (work_order.paid_amount or 0) < (work_order.total_amount or 0)
    ):
        return 0

    net_paid = max(
        0,
        (work_order.paid_amount or 0) - refunded_work_order_amount(db, work_order.id),
    )
    return min(work_order.membership_eligible_amount, net_paid)


def sync_work_order_membership_consumption(db: Session, work_order) -> int:
    current_amount = work_order.membership_consumption_amount or 0
    target_amount = calculate_work_order_membership_consumption(db, work_order)
    delta = target_amount - current_amount

    if delta:
        user = (
            db.query(models.User)
            .filter(models.User.google_id == work_order.google_id)
            .first()
        )
        if user:
            user.cumulative_consumption = max(
                0,
                (user.cumulative_consumption or 0) + delta,
            )

    work_order.membership_consumption_amount = target_amount
    from . import points as points_service

    points_service.sync_work_order_points(db, work_order)
    return delta
