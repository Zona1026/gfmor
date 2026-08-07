from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from db import models


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
    if refund.amount > max(work_order.paid_amount or 0, work_order.total_amount or 0):
        raise ValueError("Refund amount exceeds work order amount.")

    record = models.RefundRecord(
        source_type=models.AccountingSourceType.WORK_ORDER,
        source_id=work_order.id,
        work_order_id=work_order.id,
        customer_name=work_order.customer_name,
        customer_phone=work_order.customer_phone,
        amount=refund.amount,
        method=refund.method,
        reason=refund.reason,
        actor=refund.actor,
        refunded_at=datetime.utcnow(),
    )
    db.add(record)
    db.flush()

    refunded_total = _refund_total(db, models.AccountingSourceType.WORK_ORDER, work_order.id)
    if refunded_total >= (work_order.paid_amount or work_order.total_amount or 0):
        work_order.payment_status = models.WorkOrderPaymentStatus.REFUNDED
    elif refunded_total > 0:
        work_order.payment_status = models.WorkOrderPaymentStatus.PARTIALLY_PAID
    return record


def _create_shop_order_refund(db: Session, refund):
    order = db.query(models.Order).filter(models.Order.id == refund.source_id).first()
    if not order:
        raise ValueError("Shop order not found.")
    if order.source != "online":
        raise ValueError("Only online shop orders can be refunded here.")
    if refund.amount > (order.total_amount or 0):
        raise ValueError("Refund amount exceeds order amount.")

    record = models.RefundRecord(
        source_type=models.AccountingSourceType.SHOP_ORDER,
        source_id=order.id,
        order_id=order.id,
        customer_name=order.recipient_name,
        customer_phone=order.recipient_phone,
        amount=refund.amount,
        method=refund.method,
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
