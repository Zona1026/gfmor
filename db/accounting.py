from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db import models
from db import inventory as inventory_service
from db import membership as membership_service


SHOP_RECEIVABLE_STATUSES = [
    models.OrderPaymentStatus.PENDING,
    models.OrderPaymentStatus.VERIFYING,
    models.OrderPaymentStatus.FAILED,
]


def get_receipts(db: Session, skip: int = 0, limit: int = 200):
    return (
        db.query(models.PaymentRecord)
        .order_by(models.PaymentRecord.paid_at.desc(), models.PaymentRecord.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_refunds(db: Session, skip: int = 0, limit: int = 200):
    return (
        db.query(models.RefundRecord)
        .order_by(models.RefundRecord.refunded_at.desc(), models.RefundRecord.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_shop_receivables(db: Session, skip: int = 0, limit: int = 200):
    return (
        db.query(models.Order)
        .filter(
            models.Order.source == "online",
            models.Order.payment_status.in_(SHOP_RECEIVABLE_STATUSES),
        )
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def record_work_order_payment(db: Session, work_order, payment):
    existing = (
        db.query(models.PaymentRecord)
        .filter(models.PaymentRecord.work_order_payment_id == payment.id)
        .first()
    )
    if existing:
        return existing

    record = models.PaymentRecord(
        source_type=models.AccountingSourceType.WORK_ORDER,
        source_id=work_order.id,
        work_order_id=work_order.id,
        work_order_payment_id=payment.id,
        customer_name=work_order.customer_name,
        customer_phone=work_order.customer_phone,
        amount=payment.amount,
        method=payment.method,
        note=payment.note,
        paid_at=payment.paid_at or datetime.utcnow(),
    )
    db.add(record)
    return record


def update_shop_order_payment_status(db: Session, order, update):
    old_status = order.payment_status
    order.payment_status = update.payment_status

    if update.payment_status == models.OrderPaymentStatus.PAID:
        _record_shop_order_payment(db, order, update)
    elif update.payment_status == models.OrderPaymentStatus.CANCELED:
        order.payment_status = models.OrderPaymentStatus.CANCELED

    return old_status, order.payment_status


def _record_shop_order_payment(db: Session, order, update):
    existing = (
        db.query(models.PaymentRecord)
        .filter(
            models.PaymentRecord.source_type == models.AccountingSourceType.SHOP_ORDER,
            models.PaymentRecord.order_id == order.id,
        )
        .first()
    )
    if existing:
        existing.amount = order.total_amount or existing.amount
        existing.method = update.method or existing.method
        existing.actor = update.actor or existing.actor
        existing.note = update.note or existing.note
        return existing

    record = models.PaymentRecord(
        source_type=models.AccountingSourceType.SHOP_ORDER,
        source_id=order.id,
        order_id=order.id,
        customer_name=order.recipient_name,
        customer_phone=order.recipient_phone,
        amount=order.total_amount or 0,
        method=update.method,
        actor=update.actor,
        note=update.note,
        paid_at=datetime.utcnow(),
    )
    db.add(record)
    return record


def create_refund(db: Session, refund):
    if refund.source_type == models.AccountingSourceType.WORK_ORDER:
        return _create_work_order_refund(db, refund)
    if refund.source_type == models.AccountingSourceType.SHOP_ORDER:
        return _create_shop_order_refund(db, refund)
    raise ValueError("Refund source must be WORK_ORDER or SHOP_ORDER.")


def _create_work_order_refund(db: Session, refund):
    work_order = db.query(models.WorkOrder).filter(models.WorkOrder.id == refund.source_id).first()
    if not work_order:
        raise ValueError("Work order not found.")

    refund_type = (refund.refund_type or "PARTIAL").upper()
    inventory_action = (refund.inventory_action or "NO_CHANGE").upper()
    if refund_type not in {"PARTIAL", "PRICE_DIFFERENCE", "FULL"}:
        raise ValueError("不支援的退款類型。")
    if inventory_action not in {"NO_CHANGE", "RESTOCK_ALL"}:
        raise ValueError("不支援的庫存處理方式。")

    refunded_before = _refund_total(db, models.AccountingSourceType.WORK_ORDER, work_order.id)
    refundable_amount = max(0, (work_order.paid_amount or 0) - refunded_before)
    if refund.amount > refundable_amount:
        raise ValueError("退款金額超過目前可退款金額。")
    if refund_type == "FULL" and refund.amount != refundable_amount:
        raise ValueError("整單退款金額必須等於目前可退款金額。")
    if inventory_action == "RESTOCK_ALL" and refund_type != "FULL":
        raise ValueError("只有整單退款可以回補全部已扣庫存。")

    record = models.RefundRecord(
        source_type=models.AccountingSourceType.WORK_ORDER,
        source_id=work_order.id,
        work_order_id=work_order.id,
        customer_name=work_order.customer_name,
        customer_phone=work_order.customer_phone,
        amount=refund.amount,
        method=refund.method,
        refund_type=refund_type,
        inventory_action=inventory_action,
        reason=refund.reason,
        actor=refund.actor,
        refunded_at=datetime.utcnow(),
    )
    db.add(record)
    work_order.refund_records.append(record)
    db.flush()

    if inventory_action == "RESTOCK_ALL":
        _restore_work_order_inventory(db, work_order, record, refund.actor)

    refunded_total = _refund_total(db, models.AccountingSourceType.WORK_ORDER, work_order.id)
    net_paid = max(0, (work_order.paid_amount or 0) - refunded_total)
    if net_paid <= 0:
        work_order.payment_status = models.WorkOrderPaymentStatus.REFUNDED
    elif net_paid < (work_order.total_amount or 0):
        work_order.payment_status = models.WorkOrderPaymentStatus.PARTIALLY_PAID
    else:
        work_order.payment_status = models.WorkOrderPaymentStatus.PAID
    if refund_type == "FULL":
        work_order.status = models.WorkOrderStatus.CANCELED
    membership_service.sync_work_order_membership_consumption(db, work_order)
    return record


def _restore_work_order_inventory(db: Session, work_order, refund_record, actor: str = None):
    for line_item in work_order.line_items:
        consumed = line_item.inventory_consumed_quantity or 0
        if consumed <= 0 or not line_item.product:
            continue
        inventory_service.restore_inventory(
            db,
            line_item.product,
            consumed,
            source_type="work_order_refund",
            source_id=refund_record.id,
            actor=actor,
            reason=f"工單 #{work_order.id} 整單退款回補：{line_item.name}",
        )
        line_item.inventory_consumed_quantity = 0
        line_item.inventory_deducted = 0
        inventory_service.release_work_order_line_item(db, line_item)


def _create_shop_order_refund(db: Session, refund):
    order = db.query(models.Order).filter(models.Order.id == refund.source_id).first()
    if not order:
        raise ValueError("Shop order not found.")
    if order.source != "online":
        raise ValueError("Only online shop orders can be refunded here.")
    refunded_before = _refund_total(db, models.AccountingSourceType.SHOP_ORDER, order.id)
    refundable_amount = max(0, (order.total_amount or 0) - refunded_before)
    if refund.amount > refundable_amount:
        raise ValueError("Refund amount exceeds refundable order amount.")

    record = models.RefundRecord(
        source_type=models.AccountingSourceType.SHOP_ORDER,
        source_id=order.id,
        order_id=order.id,
        customer_name=order.recipient_name,
        customer_phone=order.recipient_phone,
        amount=refund.amount,
        method=refund.method,
        refund_type=(refund.refund_type or "PARTIAL").upper(),
        inventory_action="NO_CHANGE",
        reason=refund.reason,
        actor=refund.actor,
        refunded_at=datetime.utcnow(),
    )
    db.add(record)
    db.flush()

    refunded_total = _refund_total(db, models.AccountingSourceType.SHOP_ORDER, order.id)
    if refunded_total >= (order.total_amount or 0):
        order.payment_status = models.OrderPaymentStatus.REFUNDED
    elif refunded_total > 0:
        order.payment_status = models.OrderPaymentStatus.PARTIALLY_REFUNDED
    return record


def _refund_total(db: Session, source_type, source_id: int):
    return int(
        db.query(func.coalesce(func.sum(models.RefundRecord.amount), 0))
        .filter(
            models.RefundRecord.source_type == source_type,
            models.RefundRecord.source_id == source_id,
        )
        .scalar()
        or 0
    )


def get_payables(db: Session, skip: int = 0, limit: int = 200):
    return (
        db.query(models.Payable)
        .options(joinedload(models.Payable.payments))
        .order_by(models.Payable.created_at.desc(), models.Payable.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_payable(db: Session, data):
    if data.purchase_request_id:
        exists = db.query(models.PurchaseRequest.id).filter(models.PurchaseRequest.id == data.purchase_request_id).first()
        if not exists:
            raise ValueError("Purchase request not found.")
    payable = models.Payable(
        supplier_name=data.supplier_name,
        purchase_request_id=data.purchase_request_id,
        title=data.title,
        amount=data.amount,
        due_date=data.due_date,
        note=data.note,
    )
    db.add(payable)
    return payable


def add_payable_payment(db: Session, payable, data):
    if payable.status == models.PayableStatus.CANCELED:
        raise ValueError("Canceled payable cannot be paid.")
    paid_before = _payable_paid_total(db, payable.id)
    if data.amount > max(0, (payable.amount or 0) - paid_before):
        raise ValueError("Payment amount exceeds payable balance.")

    payment = models.PayablePayment(
        payable_id=payable.id,
        amount=data.amount,
        method=data.method,
        actor=data.actor,
        note=data.note,
        paid_at=data.paid_at or datetime.utcnow(),
    )
    db.add(payment)
    db.flush()
    sync_payable_status(db, payable)
    return payment


def _payable_paid_total(db: Session, payable_id: int):
    return db.query(func.coalesce(func.sum(models.PayablePayment.amount), 0)).filter(
        models.PayablePayment.payable_id == payable_id
    ).scalar() or 0


def sync_payable_status(db: Session, payable):
    if payable.status == models.PayableStatus.CANCELED:
        return payable.status
    paid = _payable_paid_total(db, payable.id)
    if paid <= 0:
        payable.status = models.PayableStatus.UNPAID
    elif paid < (payable.amount or 0):
        payable.status = models.PayableStatus.PARTIALLY_PAID
    else:
        payable.status = models.PayableStatus.PAID
    return payable.status
