from pydantic import BaseModel, model_validator
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
    google_id: Optional[str] = None
    guest_customer_id: Optional[int] = None
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
    customer_type: str = 'member'
    guest_customer: Optional["GuestCustomer"] = None

    class Config:
        from_attributes = True

class AdminOrderCreate(BaseModel):
    customer_type: str = 'member'
    google_id: Optional[str] = None
    guest_customer_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_notes: Optional[str] = None
    total_amount: int
    recipient_name: str
    recipient_phone: str
    notes: Optional[str] = None
    items: List[OrderItemBase] = []

    @model_validator(mode='after')
    def validate_customer(self):
        if self.customer_type == 'member' and not self.google_id:
            raise ValueError('會員訂單需要 google_id')
        if self.customer_type == 'guest':
            has_guest_id = self.guest_customer_id is not None
            has_guest_profile = bool(self.guest_name and self.guest_phone)
            if not has_guest_id and not has_guest_profile:
                raise ValueError('散客訂單需要 guest_customer_id 或姓名電話')
        if self.customer_type not in ('member', 'guest'):
            raise ValueError('customer_type 必須是 member 或 guest')
        return self


from .guest_customer import GuestCustomer

Order.model_rebuild()
