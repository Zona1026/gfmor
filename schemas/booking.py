# 引入 Pydantic 的基礎模型和其他必要類型
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 引入資料庫模型中定義的 Enum，以便在 Pydantic 模型中使用
from db.models import BookingCategory, BookingStatus

# --- 內部使用的輕量級 Schema ---
# 為了在 Booking 中顯示關聯的使用者與車輛資訊，避免循環依賴。

class User(BaseModel):
    """
    一個輕量級的使用者 Schema，專門用於在 Booking 回應中巢狀顯示。
    """
    google_id: str = Field(..., description="使用者的 Google ID")
    name: str = Field(..., description="車主姓名")
    phone: Optional[str] = Field(None, description="聯絡電話")

    class Config:
        from_attributes = True

class Motor(BaseModel):
    """
    一個輕量級的車輛 Schema，專門用於在 Booking 回應中巢狀顯示。
    """
    id: int = Field(..., description="車籍資料的唯一 ID")
    license_plate: str = Field(..., description="車牌號碼")
    model_name: Optional[str] = Field(None, description="車種")

    class Config:
        from_attributes = True

# --- 預約單 (Booking) 的 Schemas ---

class BookingBase(BaseModel):
    """
    預約單的基礎 Schema，定義了建立與讀取時共用的欄位。
    """
    google_id: str = Field(..., description="預約客戶的 Google ID")
    motor_id: int = Field(..., description="預約車輛的車籍 ID")
    booking_time: datetime = Field(..., description="客戶預約的到店時間")
    category: BookingCategory = Field(..., description="預約的服務類型 (維修/保養/諮詢)")
    notes: Optional[str] = Field(None, description="客戶在預約時留下的備註")

class BookingCreate(BookingBase):
    """
    用於「建立」一筆新預約紀錄的 Schema。
    API POST /bookings/ 的請求主體 (request body) 應符合此格式。
    status (狀態) 和 created_at (建立時間) 等欄位應由後端自動生成，不應由客戶端提供。
    """
    pass

class AdminBookingCreate(BookingBase):
    force: bool = False

class AdminCloseTimeslot(BaseModel):
    booking_time: datetime

class BookingUpdate(BaseModel):
    """
    用於「更新」一筆預約紀錄的 Schema。
    通常只用來變更預約的狀態 (例如：從 '預約中' 改為 '已結案' 或 '預約取消')。
    所有欄位都設為可選 (Optional)，因為更新時可能只會更新其中一部分。
    """
    status: Optional[BookingStatus] = Field(None, description="要更新成的狀態")
    notes: Optional[str] = Field(None, description="要更新的備註")

class Booking(BookingBase):
    """
    用於「讀取」或「回傳」一筆完整預約紀錄資訊的 Schema。
    這是 API GET /bookings/{id} 的主要回傳格式。
    """
    id: int = Field(..., description="預約單的唯一流水號")
    created_at: datetime = Field(..., description="這筆預約紀錄的建立時間")
    status: BookingStatus = Field(..., description="目前預約的狀態")
    
    # 巢狀顯示這筆預約關聯的客戶與車輛資訊
    user: User
    motor: Motor

    # orm_mode = True 的新寫法
    # 讓 Pydantic 模型可以從 ORM 物件 (如 SQLAlchemy 的模型實例) 的屬性來讀取資料
    class Config:
        from_attributes = True
