from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from db.models import AccountingSourceType, OrderPaymentStatus, PayableStatus


class PaymentRecord(BaseModel):
    id: int
    source_type: AccountingSourceType
    source_id: int
    work_order_id: Optional[int] = None
    order_id: Optional[int] = None
    work_order_payment_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    amount: int
    method: Optional[str] = None
    actor: Optional[str] = None
    note: Optional[str] = None
    paid_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RefundRecord(BaseModel):
    id: int
    source_type: AccountingSourceType
    source_id: int
    work_order_id: Optional[int] = None
    order_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    amount: int
    method: Optional[str] = None
    reason: Optional[str] = None
    actor: Optional[str] = None
    refunded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    source_type: AccountingSourceType
    source_id: int
    amount: int = Field(gt=0)
    method: Optional[str] = None
    reason: Optional[str] = None
    actor: Optional[str] = None


class ShopReceivable(BaseModel):
    id: int
    recipient_name: str
    recipient_phone: str
    total_amount: int
    payment_status: OrderPaymentStatus
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PayablePayment(BaseModel):
    id: int
    payable_id: int
    amount: int
    method: Optional[str] = None
    actor: Optional[str] = None
    note: Optional[str] = None
    paid_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class Payable(BaseModel):
    id: int
    supplier_name: str
    purchase_request_id: Optional[int] = None
    title: str
    amount: int
    paid_amount: int = 0
    balance_amount: int = 0
    due_date: Optional[datetime] = None
    status: PayableStatus
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    payments: List[PayablePayment] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PayableCreate(BaseModel):
    supplier_name: str = Field(min_length=1)
    purchase_request_id: Optional[int] = None
    title: str = Field(min_length=1)
    amount: int = Field(gt=0)
    due_date: Optional[datetime] = None
    note: Optional[str] = None


class PayablePaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    method: Optional[str] = None
    actor: Optional[str] = None
    note: Optional[str] = None
    paid_at: Optional[datetime] = None


class OrderPaymentStatusUpdate(BaseModel):
    payment_status: OrderPaymentStatus
    method: Optional[str] = None
    actor: Optional[str] = None
    note: Optional[str] = None
