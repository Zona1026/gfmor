from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from db import crud
from schemas.motor import Motor, MotorUpdate
from db.database import SessionLocal # 遵循專案模式，從此處引入 SessionLocal

router = APIRouter()

# =================================================================
# Dependency (依賴)
# =================================================================
def get_db():
    """
    這個函式會在每次 API 請求時，建立一個獨立的資料庫 Session，
    並在請求結束後自動關閉它。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================================
# API Endpoints
# =================================================================

@router.put("/{motor_id}", response_model=Motor)
def update_motor_by_id(
    motor_id: int,
    motor_in: MotorUpdate,
    db: Session = Depends(get_db), # 改為使用本地定義的 get_db
) -> Any:
    """
    根據車籍 ID 更新車籍資訊。
    """
    db_motor = crud.get_motor(db=db, motor_id=motor_id)
    if not db_motor:
        raise HTTPException(
            status_code=404,
            detail="找不到指定的車籍資料。",
        )
    
    # 這裡可以加入權限檢查，例如檢查操作者是否為車主本人或管理員
    
    updated_motor = crud.update_motor(db=db, motor_id=motor_id, motor_update=motor_in)
    return updated_motor

@router.delete("/{motor_id}", response_model=Motor, summary="軟刪除車籍資料")
def delete_motor_by_id(
    motor_id: int,
    db: Session = Depends(get_db), # 改為使用本地定義的 get_db
):
    """
    根據車籍 ID 軟刪除車籍資料。
    會將車輛的 status 設為 '已刪除'，並回傳更新後的車籍資料。
    """
    deleted_motor = crud.delete_motor(db=db, motor_id=motor_id)
    if not deleted_motor:
        raise HTTPException(
            status_code=404,
            detail="找不到指定的車籍資料。",
        )
    return deleted_motor