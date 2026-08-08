from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class AdminLogin(BaseModel):
    username: str = Field(..., description="管理員帳號")
    password: str = Field(..., description="管理員密碼")

class AdminResponse(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    access_token: str
    token_type: str = "bearer"

class AdminBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = "一般"

class AdminCreate(AdminBase):
    email: EmailStr
    password: str

class AdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class AdminPasswordResetRequest(BaseModel):
    username: str = Field(..., description="管理員帳號")
    email: EmailStr = Field(..., description="管理員帳號綁定的 Email")

class AdminPasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=20, description="重設密碼 token")
    password: str = Field(..., min_length=8, description="新密碼")

class AdminMessageResponse(BaseModel):
    message: str

class AdminDetail(AdminBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
