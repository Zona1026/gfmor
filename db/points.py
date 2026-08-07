from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models


DEFAULT_POINT_SETTING_VALUES = {
    "points_enabled": "true",
    "earn_amount_unit": "1000",
    "earn_points": "1",
    "validity_months": "6",
    "expiring_soon_days": "60",
    "redeem_enabled": "false",
    "point_value_amount": "0",
}


def _as_int(value: Any, default: int, min_value: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, parsed)


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def get_point_settings(db: Session) -> Dict[str, Any]:
    rows = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.key.in_(DEFAULT_POINT_SETTING_VALUES.keys()))
        .all()
    )
    raw = {**DEFAULT_POINT_SETTING_VALUES, **{row.key: row.value for row in rows}}

    return {
        "points_enabled": _as_bool(raw.get("points_enabled"), True),
        "earn_amount_unit": _as_int(raw.get("earn_amount_unit"), 1000, 1),
        "earn_points": _as_int(raw.get("earn_points"), 1, 0),
        "validity_months": _as_int(raw.get("validity_months"), 6, 1),
        "expiring_soon_days": _as_int(raw.get("expiring_soon_days"), 60, 0),
        "redeem_enabled": _as_bool(raw.get("redeem_enabled"), False),
        "point_value_amount": _as_int(raw.get("point_value_amount"), 0, 0),
    }


def get_settings_with_point_defaults(db: Session) -> Dict[str, str]:
    rows = db.query(models.SystemSetting).all()
    return {**DEFAULT_POINT_SETTING_VALUES, **{row.key: row.value for row in rows}}


def get_order_eligible_amount(order: models.Order) -> int:
    items_total = sum((item.unit_price or 0) * (item.quantity or 0) for item in order.items)
    total_amount = order.total_amount or 0

    if items_total <= 0:
        return 0
    if total_amount <= 0:
        return 0

    return max(0, min(items_total, total_amount))


def calculate_order_points(
    order: models.Order,
    settings: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    allow_disabled: bool = False,
) -> int:
    if settings is None:
        if db is None:
            raise ValueError("settings or db is required")
        settings = get_point_settings(db)

    if not settings["points_enabled"] and not allow_disabled:
        return 0
    if not order.google_id:
        return 0
    if order.status != models.OrderStatus.COMPLETED:
        return 0

    unit = settings["earn_amount_unit"]
    earn_points = settings["earn_points"]
    if unit <= 0 or earn_points <= 0:
        return 0

    return (get_order_eligible_amount(order) // unit) * earn_points


def get_order_point_entitlement(db: Session, order_id: int) -> int:
    return (
        db.query(func.coalesce(func.sum(models.PointTransaction.points), 0))
        .filter(
            models.PointTransaction.order_id == order_id,
            models.PointTransaction.type.in_(
                [
                    models.PointTransactionType.EARN,
                    models.PointTransactionType.REFUND_ADJUST,
                ]
            ),
        )
        .scalar()
        or 0
    )


def _consume_remaining_order_points(db: Session, order: models.Order, points_to_consume: int) -> None:
    remaining = points_to_consume
    earn_rows = (
        db.query(models.PointTransaction)
        .filter(
            models.PointTransaction.google_id == order.google_id,
            models.PointTransaction.order_id == order.id,
            models.PointTransaction.type == models.PointTransactionType.EARN,
            models.PointTransaction.remaining_points > 0,
        )
        .order_by(models.PointTransaction.expires_at.asc(), models.PointTransaction.id.asc())
        .all()
    )

    for row in earn_rows:
        if remaining <= 0:
            break
        consumed = min(row.remaining_points, remaining)
        row.remaining_points -= consumed
        remaining -= consumed


def sync_order_points(db: Session, order: models.Order) -> int:
    if not order.google_id:
        return 0

    current_entitlement = get_order_point_entitlement(db, order.id)
    settings = get_point_settings(db)
    desired_points = calculate_order_points(
        order,
        settings=settings,
        allow_disabled=current_entitlement > 0,
    )
    delta = desired_points - current_entitlement

    if delta == 0:
        return 0

    now = datetime.utcnow()
    if delta > 0:
        db.add(
            models.PointTransaction(
                google_id=order.google_id,
                order_id=order.id,
                type=models.PointTransactionType.EARN,
                points=delta,
                remaining_points=delta,
                issued_at=now,
                expires_at=add_months(now, settings["validity_months"]),
                note=f"Order #{order.id} earned points",
            )
        )
        return delta

    refund_points = abs(delta)
    _consume_remaining_order_points(db, order, refund_points)
    db.add(
        models.PointTransaction(
            google_id=order.google_id,
            order_id=order.id,
            type=models.PointTransactionType.REFUND_ADJUST,
            points=-refund_points,
            remaining_points=0,
            issued_at=now,
            note=f"Order #{order.id} point refund adjustment",
        )
    )
    return -refund_points


def expire_points(db: Session, google_id: Optional[str] = None) -> int:
    now = datetime.utcnow()
    query = db.query(models.PointTransaction).filter(
        models.PointTransaction.type == models.PointTransactionType.EARN,
        models.PointTransaction.remaining_points > 0,
        models.PointTransaction.expires_at.isnot(None),
        models.PointTransaction.expires_at <= now,
    )
    if google_id:
        query = query.filter(models.PointTransaction.google_id == google_id)

    expired_total = 0
    for row in query.all():
        points = row.remaining_points
        if points <= 0:
            continue
        row.remaining_points = 0
        expired_total += points
        db.add(
            models.PointTransaction(
                google_id=row.google_id,
                order_id=row.order_id,
                type=models.PointTransactionType.EXPIRE,
                points=-points,
                remaining_points=0,
                issued_at=now,
                note=f"Expired points from transaction #{row.id}",
            )
        )

    return expired_total


def get_user_point_summary(db: Session, google_id: str) -> Dict[str, int]:
    settings = get_point_settings(db)
    expire_points(db, google_id=google_id)

    balance = (
        db.query(func.coalesce(func.sum(models.PointTransaction.points), 0))
        .filter(models.PointTransaction.google_id == google_id)
        .scalar()
        or 0
    )

    now = datetime.utcnow()
    expiring_until = now + timedelta(days=settings["expiring_soon_days"])
    expiring_soon = (
        db.query(func.coalesce(func.sum(models.PointTransaction.remaining_points), 0))
        .filter(
            models.PointTransaction.google_id == google_id,
            models.PointTransaction.type == models.PointTransactionType.EARN,
            models.PointTransaction.remaining_points > 0,
            models.PointTransaction.expires_at.isnot(None),
            models.PointTransaction.expires_at > now,
            models.PointTransaction.expires_at <= expiring_until,
        )
        .scalar()
        or 0
    )

    return {
        "current_points": max(0, balance),
        "balance_points": balance,
        "expiring_soon_points": max(0, expiring_soon),
        "expiring_soon_days": settings["expiring_soon_days"],
    }
