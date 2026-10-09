from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
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


class ProductExtraCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0
    is_active: int = Field(1, ge=0, le=1)

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductExtraCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[int] = Field(None, ge=0, le=1)

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductExtraCategory(ProductExtraCategoryCreate):
    id: int
    class Config:
        from_attributes = True


class ProductMetadata(BaseModel):
    barcode: Optional[str] = Field(None, max_length=100, pattern=r'^[\x21-\x7e]+$')

    @field_validator('barcode', mode='before')
    @classmethod
    def clean_barcode(cls, value):
        return (value.strip() or None) if isinstance(value, str) else value

    vehicle_model: Optional[str] = Field(None, max_length=200)
    model_number: Optional[str] = Field(None, max_length=200)
    specification: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=200)
    suggested_price: Optional[int] = Field(None, ge=0)
    installation_labor: Optional[int] = Field(None, ge=0)


class ProductVehicleModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)

    @field_validator('name', mode='before')
    @classmethod
    def strip_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProductManagementMetadata(ProductMetadata):
    wholesale_price: Optional[int] = Field(None, ge=0)


class SupplierPrice(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=200)
    purchase_price: int = Field(ge=0)
    wholesale_price: Optional[int] = Field(None, ge=0)

    @field_validator('supplier_name', mode='before')
    @classmethod
    def strip_supplier_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class SupplierPrices(BaseModel):
    supplier_prices: List[SupplierPrice] = Field(default_factory=list)


class ProductBase(ProductMetadata):
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
    categories: List[ProductCategory] = Field(default_factory=list)
    extra_categories: List[ProductExtraCategory] = Field(default_factory=list)
    reserved_stock: int = 0
    available_stock: int = 0

    class Config:
        from_attributes = True


class ProductPage(BaseModel):
    items: List[Product]
    total: int
    page: int
    page_size: int
    total_pages: int


class SupplierWholesalePrice(BaseModel):
    supplier_name: str
    wholesale_price: Optional[int] = None


class AdminProduct(Product):
    supplier_wholesale_prices: List[SupplierWholesalePrice] = Field(default_factory=list)
    wholesale_price: Optional[int] = None


class AdminProductPage(ProductPage):
    items: List[AdminProduct]

class ProductCreate(ProductBase):
    """用於建立新商品（JSON 方式，不含圖片）。"""
    supplier_prices: List[SupplierPrice] = Field(default_factory=list)
    wholesale_price: Optional[int] = Field(None, ge=0)

class ProductUpdate(ProductManagementMetadata):
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
    supplier_prices: Optional[List[SupplierPrice]] = None
