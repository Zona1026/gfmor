from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List

from api.dependencies.admin_auth import auth_context, ensure_self_or_admin, ensure_self_or_super
from db import crud
from db.new_vehicle import ensure_maintenance_schedule
from schemas.motor import Motor, MotorUpdate
from schemas.new_vehicle import NewVehicleMaintenanceRecord
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

@router.get(
    "/{motor_id}/maintenance-records",
    response_model=List[NewVehicleMaintenanceRecord],
    summary="讀取會員新車保養紀錄",
)
def read_motor_maintenance_records(
    motor_id: int,
    auth=Depends(auth_context),
    db: Session = Depends(get_db),
):
    db_motor = crud.get_motor(db=db, motor_id=motor_id)
    if not db_motor or db_motor.status is not None or not db_motor.is_new_vehicle:
        raise HTTPException(status_code=404, detail="找不到指定的新車保養紀錄。")

    ensure_self_or_admin(db_motor.google_id, auth)
    ensure_maintenance_schedule(db, db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor.new_vehicle_maintenance_records

@router.put("/{motor_id}", response_model=Motor)
def update_motor_by_id(
    motor_id: int,
    motor_in: MotorUpdate,
    auth=Depends(auth_context),
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
    
    ensure_self_or_super(db_motor.google_id, auth)

    try:
        return crud.update_motor(db=db, motor_id=motor_id, motor_update=motor_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{motor_id}", response_model=Motor, summary="軟刪除車籍資料")
def delete_motor_by_id(
    motor_id: int,
    auth=Depends(auth_context),
    db: Session = Depends(get_db), # 改為使用本地定義的 get_db
):
    """
    根據車籍 ID 軟刪除車籍資料。
    會將車輛的 status 設為 '已刪除'，並回傳更新後的車籍資料。
    """
    db_motor = crud.get_motor(db=db, motor_id=motor_id)
    if not db_motor:
        raise HTTPException(
            status_code=404,
            detail="找不到指定的車籍資料。",
        )
    ensure_self_or_super(db_motor.google_id, auth)
    deleted_motor = crud.delete_motor(db=db, motor_id=motor_id)
    return deleted_motor
