from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from db.models import OrderStatus
from .product import Product

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: int

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    product: Optional[Product] = None

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    google_id: str
    total_amount: int
    recipient_name: str
    recipient_phone: str
    shipping_address: str = '店取'
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    items: List[OrderItemBase]

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    total_amount: Optional[int] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    notes: Optional[str] = None

class Order(OrderBase):
    id: int
    status: OrderStatus
    source: str = 'online'
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem] = []

    class Config:
        from_attributes = True

class AdminOrderCreate(BaseModel):
    google_id: str
    total_amount: int
    recipient_name: str
    recipient_phone: str
    notes: Optional[str] = None
    items: List[OrderItemBase] = []
