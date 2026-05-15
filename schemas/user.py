from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from .motor import Motor, MotorCreate # 從新的 motor.py 引入車籍相關模型

# =================================================================
# Schemas for Users (使用者相關)
# =================================================================

# 使用者資料的基礎模型
class UserBase(BaseModel):
    """
    使用者共用的基礎欄位。
    """
    email: EmailStr
    name: str
    phone: Optional[str] = None

# 用於後端內部建立使用者時的模型
class UserCreate(UserBase):
    """
    用於在程式內部建立新使用者時的模型。
    """
    google_id: str
    motors: List[MotorCreate] = [] # 允許在建立使用者時，同時建立車籍資料

class TestUserCreate(BaseModel):
    """
    用於 API 請求，建立「測試用」使用者時的模型。
    不需提供 google_id，將由後端自動生成。
    """
    name: str
    email: EmailStr
    phone: Optional[str] = None
    motors: List[MotorCreate] = Field([], description="此測試使用者的車籍資料列表")


class UserUpdate(BaseModel):
    """
    用於 API 請求，更新使用者資料時的模型。
    所有欄位都是可選的，因為使用者可能只想更新部分資料。
    """
    name: Optional[str] = None
    phone: Optional[str] = None
    membership_level: Optional[str] = None
    avatar: Optional[str] = None
    admin_notes: Optional[str] = None
    motors: List[MotorCreate] = Field([], description="要為此使用者新增的車籍資料列表")

# 用於 API 回應，從資料庫讀取使用者資料時的模型
class User(UserBase):
    """
    用於 API 回應的模型，會包含 google_id 和其他非敏感的公開資訊。
    """
    google_id: str
    join_time: datetime
    membership_level: Optional[str] = None
    avatar: Optional[str] = None
    admin_notes: Optional[str] = None
    cumulative_consumption: Optional[int] = 0
    motors: List[Motor] = [] # 在回傳使用者資料時，一併回傳車籍

    class Config:
        from_attributes = True

# =================================================================
# Schemas for Search Functionality (為了搜尋功能新增的 Schemas)
# =================================================================

class UserWithMotors(User):
    """
    用於 API 回應的模型，此模型繼承自 User，並額外包含了使用者名下所有的車籍資料列表。
    主要用於姓名搜尋客戶功能的回應。
    """
    # 這個 class 現在和 User class 功能重複，但為了避免破壞既有程式碼，暫時保留。
    # 在未來的重構中可以考慮移除。
    pass
