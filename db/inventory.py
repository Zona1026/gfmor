from sqlalchemy import func
from sqlalchemy.orm import Session

from db import models

SOURCE_ORDER_ITEM = "order_item"
SOURCE_WORK_ORDER_LINE_ITEM = "work_order_line_item"
SOURCE_PURCHASE_REQUEST = "purchase_request"


def reserved_quantity(db: Session, product_id: int) -> int:
    value = (
        db.query(func.coalesce(func.sum(models.InventoryReservation.quantity), 0))
        .filter(
            models.InventoryReservation.product_id == product_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .scalar()
    )
    return int(value or 0)


def available_stock(db: Session, product) -> int:
    return max(0, (product.stock or 0) - reserved_quantity(db, product.id))


def _movement(
    db: Session,
    product,
    movement_type,
    quantity_delta: int,
    stock_before: int,
    stock_after: int,
    source_type: str = None,
    source_id: int = None,
    actor: str = None,
    reason: str = None,
):
    db.add(models.InventoryMovement(
        product_id=product.id,
        movement_type=movement_type,
        quantity_delta=quantity_delta,
        stock_before=stock_before,
        stock_after=stock_after,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    ))


def reserve_inventory(
    db: Session,
    product,
    quantity: int,
    source_type: str,
    source_id: int,
    actor: str = None,
    reason: str = None,
):
    if quantity <= 0:
        raise ValueError("Reservation quantity must be greater than 0.")
    existing = (
        db.query(models.InventoryReservation)
        .filter(
            models.InventoryReservation.source_type == source_type,
            models.InventoryReservation.source_id == source_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .first()
    )
    if existing:
        return existing

    current_available = available_stock(db, product)
    if current_available < quantity:
        raise ValueError(
            f"Product '{product.name}' available stock is not enough. Need {quantity}, available {current_available}."
        )

    reservation = models.InventoryReservation(
        product_id=product.id,
        quantity=quantity,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    )
    db.add(reservation)
    return reservation


def release_reservations(
    db: Session,
    source_type: str,
    source_id: int,
):
    reservations = (
        db.query(models.InventoryReservation)
        .filter(
            models.InventoryReservation.source_type == source_type,
            models.InventoryReservation.source_id == source_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .all()
    )
    for reservation in reservations:
        reservation.status = models.InventoryReservationStatus.RELEASED
    return reservations


def active_reservation_quantity(db: Session, source_type: str, source_id: int) -> int:
    value = (
        db.query(func.coalesce(func.sum(models.InventoryReservation.quantity), 0))
        .filter(
            models.InventoryReservation.source_type == source_type,
            models.InventoryReservation.source_id == source_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .scalar()
    )
    return int(value or 0)


def ensure_reservation_quantity(
    db: Session,
    product,
    desired_quantity: int,
    source_type: str,
    source_id: int,
    actor: str = None,
    reason: str = None,
):
    if desired_quantity < 0:
        raise ValueError("Reservation quantity cannot be negative.")

    existing = (
        db.query(models.InventoryReservation)
        .filter(
            models.InventoryReservation.source_type == source_type,
            models.InventoryReservation.source_id == source_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .first()
    )
    current_quantity = existing.quantity if existing else 0

    if desired_quantity == current_quantity:
        return existing

    if desired_quantity == 0:
        if existing:
            existing.status = models.InventoryReservationStatus.RELEASED
        return existing

    if desired_quantity > current_quantity:
        additional_quantity = desired_quantity - current_quantity
        current_available = available_stock(db, product)
        if current_available < additional_quantity:
            raise ValueError(
                f"Product '{product.name}' available stock is not enough. Need {additional_quantity}, available {current_available}."
            )

    if existing:
        existing.quantity = desired_quantity
        existing.actor = actor or existing.actor
        existing.reason = reason or existing.reason
        return existing

    reservation = models.InventoryReservation(
        product_id=product.id,
        quantity=desired_quantity,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    )
    db.add(reservation)
    return reservation


def consume_reservations(
    db: Session,
    source_type: str,
    source_id: int,
    movement_type,
    actor: str = None,
    reason: str = None,
):
    reservations = (
        db.query(models.InventoryReservation)
        .filter(
            models.InventoryReservation.source_type == source_type,
            models.InventoryReservation.source_id == source_id,
            models.InventoryReservation.status == models.InventoryReservationStatus.ACTIVE,
        )
        .all()
    )
    for reservation in reservations:
        product = reservation.product
        if not product:
            raise ValueError("Reservation product not found.")
        if (product.stock or 0) < reservation.quantity:
            raise ValueError(
                f"Product '{product.name}' stock is not enough. Need {reservation.quantity}, stock {product.stock or 0}."
            )
        stock_before = product.stock or 0
        product.stock = stock_before - reservation.quantity
        reservation.status = models.InventoryReservationStatus.CONSUMED
        _movement(
            db,
            product,
            movement_type,
            -reservation.quantity,
            stock_before,
            product.stock,
            source_type=source_type,
            source_id=source_id,
            actor=actor,
            reason=reason,
        )
    return reservations


def deduct_immediate(
    db: Session,
    product,
    quantity: int,
    movement_type,
    source_type: str,
    source_id: int,
    actor: str = None,
    reason: str = None,
):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")
    current_available = available_stock(db, product)
    if current_available < quantity:
        raise ValueError(
            f"Product '{product.name}' available stock is not enough. Need {quantity}, available {current_available}."
        )
    stock_before = product.stock or 0
    product.stock = stock_before - quantity
    _movement(
        db,
        product,
        movement_type,
        -quantity,
        stock_before,
        product.stock,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    )


def restore_inventory(
    db: Session,
    product,
    quantity: int,
    source_type: str,
    source_id: int,
    actor: str = None,
    reason: str = None,
):
    if quantity <= 0:
        return
    stock_before = product.stock or 0
    product.stock = stock_before + quantity
    _movement(
        db,
        product,
        models.InventoryMovementType.CANCEL_RESTORE,
        quantity,
        stock_before,
        product.stock,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    )


def receive_inventory(
    db: Session,
    product,
    quantity: int,
    source_type: str,
    source_id: int,
    actor: str = None,
    reason: str = None,
):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")
    stock_before = product.stock or 0
    product.stock = stock_before + quantity
    _movement(
        db,
        product,
        models.InventoryMovementType.PURCHASE_RECEIPT,
        quantity,
        stock_before,
        product.stock,
        source_type=source_type,
        source_id=source_id,
        actor=actor,
        reason=reason,
    )


def manual_adjust_inventory(db: Session, product, stock_after: int, actor: str = None, reason: str = None):
    if stock_after < 0:
        raise ValueError("Stock cannot be negative.")
    if not reason or not reason.strip():
        raise ValueError("Adjustment reason is required.")
    reserved = reserved_quantity(db, product.id)
    if stock_after < reserved:
        raise ValueError(f"Stock cannot be lower than reserved quantity ({reserved}).")
    stock_before = product.stock or 0
    product.stock = stock_after
    _movement(
        db,
        product,
        models.InventoryMovementType.MANUAL_ADJUST,
        stock_after - stock_before,
        stock_before,
        stock_after,
        source_type="manual",
        source_id=product.id,
        actor=actor,
        reason=reason.strip(),
    )


def scrap_inventory(db: Session, product, quantity: int, actor: str = None, reason: str = None):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")
    if not reason or not reason.strip():
        raise ValueError("Scrap reason is required.")
    current_available = available_stock(db, product)
    if current_available < quantity:
        raise ValueError(
            f"Product '{product.name}' available stock is not enough. Need {quantity}, available {current_available}."
        )
    stock_before = product.stock or 0
    product.stock = stock_before - quantity
    _movement(
        db,
        product,
        models.InventoryMovementType.SCRAP_OUT,
        -quantity,
        stock_before,
        product.stock,
        source_type="scrap",
        source_id=product.id,
        actor=actor,
        reason=reason.strip(),
    )


def reserve_order_item(db: Session, order_item, actor: str = None):
    return reserve_inventory(
        db,
        order_item.product,
        order_item.quantity,
        SOURCE_ORDER_ITEM,
        order_item.id,
        actor=actor,
        reason=f"Order #{order_item.order_id}",
    )


def release_order_item(db: Session, order_item):
    return release_reservations(db, SOURCE_ORDER_ITEM, order_item.id)


def consume_order_item(db: Session, order_item, actor: str = None):
    return consume_reservations(
        db,
        SOURCE_ORDER_ITEM,
        order_item.id,
        models.InventoryMovementType.SHOP_ORDER_CONSUME,
        actor=actor,
        reason=f"Order #{order_item.order_id} completed",
    )


def has_order_item_reservation(db: Session, order_item) -> bool:
    return (
        db.query(models.InventoryReservation.id)
        .filter(
            models.InventoryReservation.source_type == SOURCE_ORDER_ITEM,
            models.InventoryReservation.source_id == order_item.id,
        )
        .first()
        is not None
    )


def work_order_line_item_reserved_quantity(db: Session, line_item) -> int:
    return active_reservation_quantity(db, SOURCE_WORK_ORDER_LINE_ITEM, line_item.id)


def reserve_work_order_line_item(db: Session, line_item, quantity: int = None, actor: str = None):
    target_quantity = line_item.quantity if quantity is None else quantity
    reservation = ensure_reservation_quantity(
        db,
        line_item.product,
        target_quantity,
        SOURCE_WORK_ORDER_LINE_ITEM,
        line_item.id,
        actor=actor,
        reason=f"Work order #{line_item.work_order_id}",
    )
    line_item.inventory_reserved_quantity = target_quantity
    return reservation


def release_work_order_line_item(db: Session, line_item):
    released = release_reservations(db, SOURCE_WORK_ORDER_LINE_ITEM, line_item.id)
    line_item.inventory_reserved_quantity = 0
    return released


def consume_work_order_line_item(db: Session, line_item, actor: str = None):
    consumed = consume_reservations(
        db,
        SOURCE_WORK_ORDER_LINE_ITEM,
        line_item.id,
        models.InventoryMovementType.WORK_ORDER_CONSUME,
        actor=actor,
        reason=f"Work order #{line_item.work_order_id} in progress",
    )
    consumed_quantity = sum(reservation.quantity or 0 for reservation in consumed)
    line_item.inventory_reserved_quantity = max(0, (line_item.inventory_reserved_quantity or 0) - consumed_quantity)
    line_item.inventory_consumed_quantity = min(
        line_item.quantity or 0,
        (line_item.inventory_consumed_quantity or 0) + consumed_quantity,
    )
    line_item.inventory_deducted = 1 if (line_item.inventory_consumed_quantity or 0) >= (line_item.quantity or 0) else 0
    return consumed_quantity
