from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from db.models import WorkOrderPaymentStatus, WorkOrderServiceType, WorkOrderStatus


class CustomerVehicle(BaseModel):
    id: int
    customer_type: str
    license_plate: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None
    status: Optional[str] = None


class CustomerServiceRecord(BaseModel):
    id: int
    work_order_id: int
    service_type: WorkOrderServiceType
    status: WorkOrderStatus
    payment_status: WorkOrderPaymentStatus
    vehicle_license_plate: Optional[str] = None
    vehicle_model: Optional[str] = None
    responsible_staff: Optional[str] = None
    total_amount: int = 0
    scheduled_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class CustomerSpendingRecord(BaseModel):
    id: str
    source: str
    source_id: int
    source_label: str
    amount: int = 0
    status: str
    method: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CustomerSummary(BaseModel):
    customer_type: str
    customer_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    joined_at: Optional[datetime] = None
    vehicle_count: int = 0
    vehicle_label: Optional[str] = None
    latest_service_at: Optional[datetime] = None
    cumulative_spending: int = 0
    current_points: int = 0
    expiring_soon_points: int = 0
    has_notes: bool = False


class CustomerDetail(CustomerSummary):
    notes: Optional[str] = None
    vehicles: List[CustomerVehicle] = []
    service_records: List[CustomerServiceRecord] = []
    spending_records: List[CustomerSpendingRecord] = []
