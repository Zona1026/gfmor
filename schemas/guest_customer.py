from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class GuestMotorBase(BaseModel):
    license_plate: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None


class GuestMotorCreate(GuestMotorBase):
    pass


class GuestMotorUpdate(BaseModel):
    license_plate: Optional[str] = None
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None
    status: Optional[str] = None


class GuestMotor(GuestMotorBase):
    id: int
    guest_customer_id: int
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GuestCustomerBase(BaseModel):
    name: str
    phone: str
    notes: Optional[str] = None


class GuestCustomerCreate(GuestCustomerBase):
    pass


class GuestCustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


class GuestCustomer(GuestCustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    motors: List[GuestMotor] = []

    class Config:
        from_attributes = True


class GuestCustomerMerge(BaseModel):
    google_id: str
