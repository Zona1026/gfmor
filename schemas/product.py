from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.models import InventoryType


class ProductCategoryBase(BaseModel):
    name: str
    sort_order: int = 0
    is_active: int = 1


class ProductCategoryCreate(ProductCategoryBase):
    pass


class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None


class ProductCategory(ProductCategoryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    """所有商品相關操作共用的基礎欄位。"""
    name: str
    description: Optional[str] = None
    price: int
    stock: int
    inventory_type: InventoryType = InventoryType.BOTH
    low_stock_threshold: int = 5
    category_id: Optional[int] = None
    category: Optional[str] = None

class Product(ProductBase):
    """用於 API 回應的模型。"""
    id: int
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    is_active: int = 1
    created_at: Optional[datetime] = None
    category_info: Optional[ProductCategory] = None
    reserved_stock: int = 0
    available_stock: int = 0

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
    inventory_type: Optional[InventoryType] = None
    low_stock_threshold: Optional[int] = None
    category_id: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    is_active: Optional[int] = None
