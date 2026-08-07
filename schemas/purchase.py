from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from db.models import PurchaseRequestStatus, WorkOrderStatus


class PurchaseProductSummary(BaseModel):
    id: int
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseWorkOrderSummary(BaseModel):
    id: int
    status: WorkOrderStatus
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_license_plate: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseLineItemSummary(BaseModel):
    id: int
    name: str
    quantity: int
    inventory_reserved_quantity: int = 0
    inventory_consumed_quantity: int = 0
    inventory_shortage_quantity: int = 0

    class Config:
        from_attributes = True


class PurchaseReceipt(BaseModel):
    id: int
    purchase_request_id: int
    quantity: int
    actor: Optional[str] = None
    note: Optional[str] = None
    received_at: datetime

    class Config:
        from_attributes = True


class PurchaseAssignment(BaseModel):
    id: int
    purchase_request_id: int
    work_order_id: int
    work_order_line_item_id: int
    quantity: int
    actor: Optional[str] = None
    note: Optional[str] = None
    assigned_at: datetime

    class Config:
        from_attributes = True


class PurchaseRequest(BaseModel):
    id: int
    product_id: int
    work_order_id: Optional[int] = None
    work_order_line_item_id: Optional[int] = None
    item_name: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    requested_quantity: int
    ordered_quantity: int = 0
    arrived_quantity: int = 0
    assigned_quantity: int = 0
    unassigned_arrived_quantity: int = 0
    status: PurchaseRequestStatus
    supplier_name: Optional[str] = None
    expected_arrival_date: Optional[datetime] = None
    responsible_staff: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    product: Optional[PurchaseProductSummary] = None
    work_order: Optional[PurchaseWorkOrderSummary] = None
    work_order_line_item: Optional[PurchaseLineItemSummary] = None
    receipts: List[PurchaseReceipt] = Field(default_factory=list)
    assignments: List[PurchaseAssignment] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PurchaseOrderUpdate(BaseModel):
    supplier_name: Optional[str] = None
    expected_arrival_date: Optional[datetime] = None
    ordered_quantity: Optional[int] = Field(default=None, ge=1)
    responsible_staff: Optional[str] = None
    note: Optional[str] = None


class PurchaseReceiveCreate(BaseModel):
    quantity: int = Field(gt=0)
    actor: Optional[str] = None
    note: Optional[str] = None


class PurchaseAssignCreate(BaseModel):
    work_order_id: int
    work_order_line_item_id: int
    quantity: Optional[int] = Field(default=None, gt=0)
    actor: Optional[str] = None
    note: Optional[str] = None


class PurchaseCancelCreate(BaseModel):
    actor: Optional[str] = None
    note: Optional[str] = None
