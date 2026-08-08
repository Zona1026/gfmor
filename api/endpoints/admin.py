from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import secrets
from urllib.parse import quote

from db import database, models, crud
from schemas import admin as admin_schema
from schemas import booking as booking_schema
from api.dependencies.admin_auth import require_manager_admin
from core.config import settings
from core.email import send_plain_email
from core.security import verify_password, create_access_token, get_password_hash

router = APIRouter()


PASSWORD_RESET_REQUEST_MESSAGE = "若帳號與 Email 相符，重設密碼連結已寄出，請到信箱查看。"


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _get_shop_name(db: Session) -> str:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "store_name").first()
    return setting.value if setting and setting.value else "GFmoter"


def _build_reset_email_body(admin: models.Admin, reset_url: str, shop_name: str) -> str:
    display_name = admin.full_name or admin.username
    return (
        f"{display_name} 您好：\n\n"
        f"我們收到 {shop_name} 店家後台密碼重設申請。\n"
        "請點擊下方連結設定新密碼：\n\n"
        f"{reset_url}\n\n"
        f"此連結將於 {settings.ADMIN_PASSWORD_RESET_EXPIRE_MINUTES} 分鐘後失效，且只能使用一次。\n"
        "如果不是您本人申請，請忽略此信並通知系統管理人員。\n"
    )


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
    # 我們可以在 token 的 payload 裡加上 role="admin" 以快速識別，並附帶具體管理員權限
    access_token = create_access_token(
        data={"sub": admin.username, "role": "admin", "admin_role": admin.role}, expires_delta=access_token_expires
    )

    return {
        "username": admin.username,
        "full_name": admin.full_name,
        "role": admin.role,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post(
    "/password-reset/request",
    response_model=admin_schema.AdminMessageResponse,
    summary="申請管理員自助重設密碼",
)
def request_admin_password_reset(
    payload: admin_schema.AdminPasswordResetRequest,
    db: Session = Depends(database.get_db),
):
    username = payload.username.strip()
    email = _normalize_email(str(payload.email))
    admin = db.query(models.Admin).filter(models.Admin.username == username).first()

    if not admin or not admin.email or _normalize_email(admin.email) != email:
        return {"message": PASSWORD_RESET_REQUEST_MESSAGE}

    token = secrets.token_urlsafe(32)
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/admin-reset-password?token={quote(token)}"
    now = datetime.utcnow()

    admin.password_reset_token_hash = _hash_reset_token(token)
    admin.password_reset_expires_at = now + timedelta(minutes=settings.ADMIN_PASSWORD_RESET_EXPIRE_MINUTES)
    admin.password_reset_requested_at = now

    shop_name = _get_shop_name(db)
    subject = f"{shop_name} 店家後台密碼重設"
    body = _build_reset_email_body(admin, reset_url, shop_name)

    try:
        send_plain_email(admin.email, subject, body)
    except RuntimeError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="系統尚未設定寄信服務，無法自助重設密碼。",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="重設密碼信件寄送失敗，請稍後再試或聯絡系統維護人員。",
        )

    db.commit()
    return {"message": PASSWORD_RESET_REQUEST_MESSAGE}


@router.post(
    "/password-reset/confirm",
    response_model=admin_schema.AdminMessageResponse,
    summary="確認管理員自助重設密碼",
)
def confirm_admin_password_reset(
    payload: admin_schema.AdminPasswordResetConfirm,
    db: Session = Depends(database.get_db),
):
    token_hash = _hash_reset_token(payload.token)
    admin = db.query(models.Admin).filter(models.Admin.password_reset_token_hash == token_hash).first()

    if not admin or not admin.password_reset_expires_at or admin.password_reset_expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="重設連結無效或已過期")

    admin.hashed_password = get_password_hash(payload.password)
    admin.password_reset_token_hash = None
    admin.password_reset_expires_at = None
    admin.password_reset_requested_at = None
    db.commit()

    return {"message": "密碼已更新，請使用新密碼登入。"}

@router.post("/bookings", response_model=booking_schema.Booking, summary="管理員手動新增預約單")
def create_admin_booking(
    booking: booking_schema.AdminBookingCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(database.get_db),
):
    try:
        return crud.create_booking(db=db, booking=booking, force=booking.force)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/bookings/close", response_model=booking_schema.Booking, summary="關閉特定時段")
def close_timeslot(
    close_data: booking_schema.AdminCloseTimeslot,
    admin=Depends(require_manager_admin),
    db: Session = Depends(database.get_db),
):
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
