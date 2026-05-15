# 引入 FastAPI 和相關模組
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# 引入資料庫 CRUD 函式、schemas 和資料庫 session 管理
from db import crud, models
from schemas import booking as booking_schema
from db.database import SessionLocal

# 建立一個給這個 endpoint 用的 router
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

@router.post(
    "/",
    response_model=booking_schema.Booking,
    status_code=status.HTTP_201_CREATED,
    summary="建立新預約單"
)
def create_booking(booking: booking_schema.BookingCreate, db: Session = Depends(get_db)):
    """
    建立一筆新的預約紀錄。

    - **google_id**: 預約客戶的 Google ID (必填)。
    - **motor_id**: 預約車輛的車籍 ID (必填)。
    - **booking_time**: 預約的日期與時間 (必填)。
    - **category**: 服務類型 (可選: '維修', '保養', '諮詢') (必填)。
    - **notes**: 客戶備註 (選填)。

    **注意**: 後端會驗證客戶與車輛是否存在，以及兩者是否匹配。
    """
    try:
        # 呼叫 CRUD 層的函式來執行建立預約單的邏輯
        return crud.create_booking(db=db, booking=booking)
    except ValueError as e:
        # 如果 CRUD 層在驗證時發現問題 (例如客戶不存在、車輛不匹配)，會拋出 ValueError。
        # 我們在此捕捉錯誤，並回傳一個 HTTP 400 (客戶端錯誤) 的回應。
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[booking_schema.Booking], summary="讀取預約單列表")
def read_bookings(skip: int = 0, limit: int = 100, date_str: str = None, db: Session = Depends(get_db)):
    """
    讀取資料庫中的預約單列表，預設按預約時間由新到舊排序。
    可使用 `skip` 和 `limit` 參數來進行分頁，也可加上 date_str 篩選。
    """
    bookings = crud.get_bookings(db, skip=skip, limit=limit, date_str=date_str)
    return bookings

@router.get("/date/{date_str}", response_model=List[booking_schema.Booking], summary="讀取特定日期的預約單")
def read_bookings_by_date(date_str: str, db: Session = Depends(get_db)):
    """
    讀取特定日期的所有 PENDING 預約紀錄。
    日期格式需為 YYYY-MM-DD。
    """
    try:
        bookings = crud.get_bookings_by_date(db, date_str=date_str)
        return bookings
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/user/{google_id}", response_model=List[booking_schema.Booking], summary="讀取特定使用者的預約單")
def read_user_bookings(google_id: str, db: Session = Depends(get_db)):
    """
    讀取特定使用者的所有預約單紀錄。
    """
    bookings = db.query(models.Booking).filter(models.Booking.google_id == google_id).order_by(models.Booking.booking_time.desc()).all()
    return bookings

@router.get("/{booking_id}", response_model=booking_schema.Booking, summary="讀取單一預約單")
def read_booking(booking_id: int, db: Session = Depends(get_db)):
    """
    根據預約單 `booking_id` 讀取單一預約單的詳細資料。
    """
    db_booking = crud.get_booking(db, booking_id=booking_id)
    if db_booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該預約單")
    return db_booking

@router.put("/{booking_id}", response_model=booking_schema.Booking, summary="更新預約單狀態或備註")
def update_booking(
    booking_id: int,
    booking: booking_schema.BookingUpdate,
    db: Session = Depends(get_db)
):
    """
    根據預約單 `booking_id` 更新其資訊。
    主要用於變更預約狀態 (例如：'預約中' -> '已結案') 或修改備註。
    """
    db_booking = crud.update_booking(db, booking_id=booking_id, booking_update=booking)
    if db_booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該預約單")
    return db_booking
