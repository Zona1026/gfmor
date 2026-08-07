from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from db.models import InventoryMovementType, InventoryReservationStatus, InventoryType
from schemas.product import ProductCategory


class InventoryProduct(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    category_info: Optional[ProductCategory] = None
    inventory_type: InventoryType
    low_stock_threshold: int
    available_stock: int
    stock: Optional[int] = None
    reserved_stock: Optional[int] = None
    is_low_stock: bool = False


class InventoryMovement(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    movement_type: InventoryMovementType
    quantity_delta: int
    stock_before: int
    stock_after: int
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    actor: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryReservation(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    status: InventoryReservationStatus
    source_type: str
    source_id: int
    actor: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryAdjustmentCreate(BaseModel):
    product_id: int
    stock_after: int = Field(ge=0)
    reason: str = Field(min_length=1)
    actor: Optional[str] = None


class InventoryReservationReleaseCreate(BaseModel):
    reason: str = Field(min_length=1)
    actor: Optional[str] = None


class InventoryScrapCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1)
    actor: Optional[str] = None
