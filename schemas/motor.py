from pydantic import BaseModel, Field
from typing import Optional

class MotorBase(BaseModel):
    """
    車籍資料共用的基礎欄位。
    """
    license_plate: Optional[str] = Field(None, description="車牌號碼")
    brand: Optional[str] = Field(None, description="廠牌")
    model_name: Optional[str] = Field(None, description="型號")
    vin: Optional[str] = Field(None, description="引擎號碼")
    mileage: Optional[int] = Field(None, description="里程數")

class MotorCreate(MotorBase):
    """
    用於 API 請求，建立新車籍資料時的模型。
    """
    # 建立時車牌是必須的
    license_plate: str = Field(..., description="車牌號碼")
    
class MotorUpdate(BaseModel):
    """
    用於 API 請求，更新車籍資料時的模型。
    所有欄位都是可選的。
    """
    license_plate: Optional[str] = None
    brand: Optional[str] = None
    model_name: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None

class Motor(MotorBase):
    """
    用於 API 回應，從資料庫讀取車籍資料時的模型。
    """
    id: int
    google_id: str # 車主是誰
    status: Optional[str] = Field(None, description="狀態，'已刪除' 表示被軟刪除")

    class Config:
        from_attributes = True
