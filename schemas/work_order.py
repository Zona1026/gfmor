from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from db.models import (
    BookingCategory,
    PurchaseRequestStatus,
    WorkOrderApprovalStatus,
    WorkOrderApprovalType,
    WorkOrderLineItemType,
    WorkOrderPaymentStatus,
    WorkOrderServiceType,
    WorkOrderStatus,
)


class Product(BaseModel):
    id: int
    name: str
    price: int

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    google_id: str
    name: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class GuestCustomerSummary(BaseModel):
    id: int
    name: str
    phone: str

    class Config:
        from_attributes = True


class MotorSummary(BaseModel):
    id: int
    license_plate: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None

    class Config:
        from_attributes = True


class GuestMotorSummary(BaseModel):
    id: int
    license_plate: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None

    class Config:
        from_attributes = True


class BookingSummary(BaseModel):
    id: int
    booking_time: datetime
    category: BookingCategory
    notes: Optional[str] = None
    user: UserSummary
    motor: MotorSummary

    class Config:
        from_attributes = True


class WorkOrderItemBase(BaseModel):
    product_id: int
    quantity: int


class WorkOrderItemCreate(WorkOrderItemBase):
    pass


class WorkOrderItem(WorkOrderItemBase):
    id: int
    unit_price: int
    product: Product

    class Config:
        from_attributes = True


class WorkOrderLineItemBase(BaseModel):
    type: WorkOrderLineItemType
    name: str
    description: Optional[str] = None
    product_id: Optional[int] = None
    quantity: int = Field(default=1, gt=0)
    unit_price: int = 0
    is_confirmed: int = 1
    counts_toward_membership: bool = False


class WorkOrderLineItemCreate(WorkOrderLineItemBase):
    pass


class WorkOrderLineItemUpdate(WorkOrderLineItemBase):
    id: Optional[int] = None


class WorkOrderPurchaseRequestSummary(BaseModel):
    id: int
    requested_quantity: int
    ordered_quantity: int = 0
    arrived_quantity: int = 0
    assigned_quantity: int = 0
    unassigned_arrived_quantity: int = 0
    status: PurchaseRequestStatus
    supplier_name: Optional[str] = None
    expected_arrival_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderLineItem(WorkOrderLineItemBase):
    id: int
    inventory_reserved_quantity: int = 0
    inventory_consumed_quantity: int = 0
    inventory_shortage_quantity: int = 0
    inventory_deducted: int = 0
    fulfillment_status: Optional[str] = None
    fulfillment_status_updated_at: Optional[datetime] = None
    line_total: int = 0
    product: Optional[Product] = None
    purchase_requests: List[WorkOrderPurchaseRequestSummary] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderLineItemFulfillmentStatusUpdate(BaseModel):
    status: Literal["RESERVED", "ORDERED", "ARRIVED"]


class WorkOrderPaymentCreate(BaseModel):
    amount: int
    method: Optional[str] = None
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class WorkOrderPayment(WorkOrderPaymentCreate):
    id: int
    paid_at: datetime

    class Config:
        from_attributes = True


class WorkOrderApproval(BaseModel):
    id: int
    work_order_id: int
    type: WorkOrderApprovalType
    title: str
    reason: Optional[str] = None
    status: WorkOrderApprovalStatus
    requested_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    note: Optional[str] = None
    work_order: Optional["WorkOrderApprovalWorkOrderSummary"] = None

    class Config:
        from_attributes = True


class WorkOrderApprovalReview(BaseModel):
    reviewed_by: Optional[str] = None
    note: Optional[str] = None


class WorkOrderSupervisorReview(BaseModel):
    reviewed_by: Optional[str] = None


class WorkOrderReopenCreate(BaseModel):
    reason: str = Field(min_length=1)
    actor: Optional[str] = None


class WorkOrderRevisionRefundCreate(BaseModel):
    method: Optional[str] = None
    note: Optional[str] = None
    actor: Optional[str] = None


class WorkOrderRefundCreate(BaseModel):
    refund_type: Literal["PRICE_DIFFERENCE", "FULL"]
    amount: int = Field(gt=0)
    method: str = Field(min_length=1)
    inventory_action: Literal["NO_CHANGE", "RESTOCK_ALL"] = "NO_CHANGE"
    reason: str = Field(min_length=1)
    actor: Optional[str] = None


class WorkOrderRefundRecord(BaseModel):
    id: int
    amount: int
    method: Optional[str] = None
    refund_type: str = "PARTIAL"
    inventory_action: str = "NO_CHANGE"
    reason: Optional[str] = None
    actor: Optional[str] = None
    refunded_at: datetime

    class Config:
        from_attributes = True


class WorkOrderRevision(BaseModel):
    id: int
    work_order_id: int
    reason: str
    actor: Optional[str] = None
    previous_status: str
    previous_total_amount: int
    previous_paid_amount: int
    refund_due_amount: int = 0
    refund_status: str = "NONE"
    refund_record_id: Optional[int] = None
    reopened_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderApprovalWorkOrderSummary(BaseModel):
    id: int
    customer_name: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    total_amount: int = 0
    status: WorkOrderStatus

    class Config:
        from_attributes = True


class WorkOrderBase(BaseModel):
    booking_id: Optional[int] = None
    google_id: Optional[str] = None
    guest_customer_id: Optional[int] = None
    guest_motor_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    motor_id: Optional[int] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None
    vehicle_is_new: Optional[bool] = None
    vehicle_purchase_date: Optional[date] = None
    service_type: Optional[WorkOrderServiceType] = None
    problem_description: Optional[str] = None
    inspection_result: Optional[str] = None
    responsible_staff: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    ordered_date: Optional[date] = None
    consumption_date: Optional[date] = None
    notes: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    line_items: List[WorkOrderLineItemCreate] = Field(default_factory=list)
    # Backward-compatible payload used by the previous appointment conversion UI.
    items: List[WorkOrderItemCreate] = Field(default_factory=list)


class WorkOrderUpdate(BaseModel):
    status: Optional[WorkOrderStatus] = None
    payment_status: Optional[WorkOrderPaymentStatus] = None
    service_type: Optional[WorkOrderServiceType] = None
    problem_description: Optional[str] = None
    inspection_result: Optional[str] = None
    responsible_staff: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    ordered_date: Optional[date] = None
    notes: Optional[str] = None
    line_items: Optional[List[WorkOrderLineItemUpdate]] = None


class WorkOrderDeleteCreate(BaseModel):
    reason: str = Field(min_length=1)
    actor: Optional[str] = None


class WorkOrder(BaseModel):
    id: int
    booking_id: Optional[int] = None
    google_id: Optional[str] = None
    guest_customer_id: Optional[int] = None
    guest_motor_id: Optional[int] = None
    motor_id: Optional[int] = None
    customer_type: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_vin: Optional[str] = None
    vehicle_mileage: Optional[int] = None
    service_type: WorkOrderServiceType
    problem_description: Optional[str] = None
    inspection_result: Optional[str] = None
    status: WorkOrderStatus
    payment_status: WorkOrderPaymentStatus
    responsible_staff: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    ordered_date: date
    consumption_date: date
    total_amount: int
    membership_eligible_amount: int = 0
    membership_consumption_amount: int = 0
    paid_amount: int = 0
    refunded_amount: int = 0
    net_paid_amount: int = 0
    refundable_amount: int = 0
    balance_amount: int = 0
    notes: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    supervisor_reviewed_at: Optional[datetime] = None
    supervisor_reviewed_by: Optional[str] = None
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    delete_reason: Optional[str] = None
    items: List[WorkOrderItem] = Field(default_factory=list)
    line_items: List[WorkOrderLineItem] = Field(default_factory=list)
    payments: List[WorkOrderPayment] = Field(default_factory=list)
    refund_records: List[WorkOrderRefundRecord] = Field(default_factory=list)
    approvals: List[WorkOrderApproval] = Field(default_factory=list)
    revisions: List[WorkOrderRevision] = Field(default_factory=list)
    approval_status: Optional[WorkOrderApprovalStatus] = None
    inventory_reservation_pending: bool = False
    inventory_reserved: bool = False
    inventory_consumption_pending: bool = False
    inventory_consumed: bool = False
    booking: Optional[BookingSummary] = None
    user: Optional[UserSummary] = None
    guest_customer: Optional[GuestCustomerSummary] = None
    guest_motor: Optional[GuestMotorSummary] = None
    motor: Optional[MotorSummary] = None

    class Config:
        from_attributes = True


WorkOrderApproval.model_rebuild()
