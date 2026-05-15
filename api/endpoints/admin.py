from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from db import database, models, crud
from schemas import admin as admin_schema
from schemas import booking as booking_schema
from core.config import settings
from core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/login", response_model=admin_schema.AdminResponse, summary="管理員登入")
def login_admin(login_data: admin_schema.AdminLogin, db: Session = Depends(database.get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == login_data.username).first()
    if not admin or not verify_password(login_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 建立 Access Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 我們可以在 token 的 payload 裡加上 role="admin" 以快速識別
    access_token = create_access_token(
        data={"sub": admin.username, "role": "admin"}, expires_delta=access_token_expires
    )

    return {
        "username": admin.username,
        "full_name": admin.full_name,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/bookings", response_model=booking_schema.Booking, summary="管理員手動新增預約單")
def create_admin_booking(booking: booking_schema.AdminBookingCreate, db: Session = Depends(database.get_db)):
    try:
        return crud.create_booking(db=db, booking=booking, force=booking.force)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/bookings/close", response_model=booking_schema.Booking, summary="關閉特定時段")
def close_timeslot(close_data: booking_schema.AdminCloseTimeslot, db: Session = Depends(database.get_db)):
    try:
        sys_motor = db.query(models.Motor).filter(models.Motor.google_id == "system").first()
        if not sys_motor:
            raise ValueError("請先初始化 system 幽靈車輛。")
            
        dummy_booking = booking_schema.BookingCreate(
            google_id="system",
            motor_id=sys_motor.id,
            booking_time=close_data.booking_time,
            category="維修",
            notes="時段關閉"
        )
        return crud.create_booking(db=db, booking=dummy_booking, force=True, is_system_close=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
