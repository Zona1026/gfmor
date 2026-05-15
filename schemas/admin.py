from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AdminLogin(BaseModel):
    username: str = Field(..., description="管理員帳號")
    password: str = Field(..., description="管理員密碼")

class AdminResponse(BaseModel):
    username: str
    full_name: Optional[str] = None
    access_token: str
    token_type: str = "bearer"

class AdminBase(BaseModel):
    username: str
    full_name: Optional[str] = None

class AdminCreate(AdminBase):
    password: str

class AdminUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class AdminDetail(AdminBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
