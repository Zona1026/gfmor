from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AnnouncementBase(BaseModel):
    title: str = Field(..., description="公告標題")
    description: Optional[str] = Field(None, description="公告描述")

class AnnouncementCreate(AnnouncementBase):
    image_url: str
    cloudinary_public_id: Optional[str] = None
    sort_order: int = 0

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None

class Announcement(AnnouncementBase):
    id: int
    image_url: str
    cloudinary_public_id: Optional[str] = None
    sort_order: int = 0
    is_active: int = 1
    created_at: datetime

    class Config:
        from_attributes = True
