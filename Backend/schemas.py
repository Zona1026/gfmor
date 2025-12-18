# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# 前端只需要傳一個 token 過來 (保持不變)
class GoogleLoginRequest(BaseModel):
    token: str

# 更新電話的請求格式 (保持不變)
class PhoneUpdateRequest(BaseModel):
    google_id: str 
    phone: str = Field(..., pattern=r"^\d{10}$", description="必須是10碼數字")

# --- 【以下是新增的】 ---

# 1. 建立預約的請求資料
class BookingCreate(BaseModel):
    user_google_id: str
    car_model: str
    booking_time: datetime
    category: str
    engine_no: Optional[str] = None
    note: Optional[str] = None

# 2. 回傳預約的資料格式
class BookingResponse(BaseModel):
    booking_id: int
    booking_time: datetime
    car_model: str
    category: str
    status: str
    created_at: datetime
    note: Optional[str]

    class Config:
        orm_mode = True # 讓 Pydantic 可以讀取 SQLAlchemy 物件

# 3. 管理員設定時段容量的請求
class SlotConfigCreate(BaseModel):
    target_time: datetime
    max_capacity: int

# 4. 回傳時段設定
class SlotConfigResponse(BaseModel):
    target_time: datetime
    max_capacity: int
    
    class Config:
        orm_mode = True

# 回傳給前端的消費紀錄格式
class ConsumptionResponse(BaseModel):
    id: int
    amount: int
    description: str
    created_at: datetime

    class Config:
        orm_mode = True

# 管理員新增消費的請求格式
class CreateConsumption(BaseModel):
    user_google_id: str
    amount: int
    description: str