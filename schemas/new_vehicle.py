from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NewVehicleMaintenanceRecordUpdate(BaseModel):
    service_date: Optional[date] = None
    actual_mileage: Optional[int] = Field(None, ge=0)
    engine_oil: Optional[bool] = None
    gear_oil: Optional[bool] = None
    air_filter: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=255)


class NewVehicleMaintenanceRecord(BaseModel):
    id: int
    target_mileage: int
    service_date: Optional[date] = None
    actual_mileage: Optional[int] = None
    engine_oil: bool
    gear_oil: bool
    air_filter: bool
    notes: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class NewVehicleProfile(BaseModel):
    vehicle_type: str
    vehicle_id: int
    customer_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    license_plate: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    purchase_date: Optional[date] = None
    current_mileage: Optional[int] = None
    records: List[NewVehicleMaintenanceRecord] = Field(default_factory=list)
