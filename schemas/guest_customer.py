from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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

    class Config:
        from_attributes = True


class GuestCustomerMerge(BaseModel):
    google_id: str
