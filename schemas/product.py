from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    """所有商品相關操作共用的基礎欄位。"""
    name: str
    description: Optional[str] = None
    price: int
    stock: int
    category: Optional[str] = None

class Product(ProductBase):
    """用於 API 回應的模型。"""
    id: int
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    is_active: int = 1
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductCreate(ProductBase):
    """用於建立新商品（JSON 方式，不含圖片）。"""
    pass

class ProductUpdate(BaseModel):
    """用於更新商品，所有欄位可選。"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    is_active: Optional[int] = None
