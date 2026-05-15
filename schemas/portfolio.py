from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PortfolioBase(BaseModel):
    title: str = Field(..., description="作品標題")
    category: str = Field(..., description="分類：level-1 / level-2 / level-3 / level-4")
    description: Optional[str] = Field(None, description="作品描述")

class PortfolioCreate(PortfolioBase):
    image_url: str
    cloudinary_public_id: Optional[str] = None

class PortfolioUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None

class Portfolio(PortfolioBase):
    id: int
    image_url: str
    cloudinary_public_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
