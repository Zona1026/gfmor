from sqlalchemy.orm import Session

# 引入我們建立的 models 和 schemas
from . import models
from schemas.user import UserCreate, UserUpdate
from schemas.product import ProductCreate, ProductUpdate

# =================================================================
# User CRUD (使用者相關)
# =================================================================

def get_user(db: Session, google_id: str):
    """
    根據 Google ID 獲取單一使用者。
    """
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def get_user_by_email(db: Session, email: str):
    """
    根據 Email 獲取單一使用者。
    """
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """
    獲取使用者列表，支援分頁。
    """
    return db.query(models.User).offset(skip).limit(limit).all()

def get_users_by_name(db: Session, name: str, skip: int = 0, limit: int = 10):
    """
    根據姓名模糊搜尋使用者。
    """
    if not name:
        return []
    search_pattern = f"%{name}%"
    # 使用 ilike 進行不區分大小寫的模糊搜尋
    return db.query(models.User).filter(models.User.name.ilike(search_pattern)).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    """
    建立新使用者，並可選擇性地同時建立其車籍資料。
    """
    # 先將車籍資料從 user DTO 中分離出來
    motors_data = user.motors
    # 使用 exclude 參數來建立一個不含 'motors' 的字典
    user_data = user.dict(exclude={'motors'})

    # 根據過濾後的資料建立 User 物件
    db_user = models.User(**user_data)
    db.add(db_user)
    
    # 先提交一次，這樣 db_user 才能獲得由資料庫產生的 id
    # 並且讓後續的關聯操作可以找到這位使用者
    db.commit()
    db.refresh(db_user)

    # 如果有提供車籍資料，則逐一建立
    if motors_data:
        for motor_data in motors_data:
            db_motor = models.Motor(
                **motor_data.dict(),
                google_id=db_user.google_id  # 確保車輛關聯到這位新使用者
            )
            db.add(db_motor)
        
        # 再次提交，以儲存新建立的車籍資料
        db.commit()
        # 刷新使用者物件以載入剛建立的關聯車輛
        db.refresh(db_user)

    return db_user

def update_user(db: Session, google_id: str, user_update: UserUpdate):
    """
    根據 Google ID 更新使用者資訊，並可選擇性地為其新增車籍資料。
    """
    db_user = get_user(db, google_id=google_id)
    if not db_user:
        return None
    
    # 分離出車籍資料和使用者基本資料
    motors_data = user_update.motors
    update_data = user_update.dict(exclude_unset=True, exclude={'motors'})

    # 1. 更新使用者基本欄位
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)

    # 2. 如果有提供新的車籍資料，則逐一建立
    if motors_data:
        for motor_data in motors_data:
            # 檢查該車牌是否已存在
            existing_motor = db.query(models.Motor).filter(models.Motor.license_plate == motor_data.license_plate).first()
            if existing_motor:
                # 如果車牌已存在且屬於同一位使用者，我們就跳過新增 (或者在此更新)
                if existing_motor.google_id == db_user.google_id:
                    continue
                else:
                    raise ValueError(f"車牌 '{motor_data.license_plate}' 已經被其他使用者註冊了！")
            
            new_motor = models.Motor(
                **motor_data.dict(),
                google_id=db_user.google_id  # 確保新車輛關聯到這位使用者
            )
            db.add(new_motor)
            
    # 3. 提交所有變更 (包含使用者更新和新增的車輛)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        
    # 刷新使用者物件，以載入所有關聯資料 (包括剛才新增的車輛)
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, google_id: str):
    """
    根據 Google ID 刪除使用者 (安全刪除)。
    如果使用者底下還有車籍、預約、或訂單紀錄，將不允許刪除。
    """
    db_user = get_user(db, google_id=google_id)
    if not db_user:
        # 如果使用者不存在，也算是一種「成功刪除」的情境，回傳 True
        return True
    
    # 檢查關聯紀錄
    if db_user.motors or db_user.bookings or db_user.orders:
        raise ValueError(f"無法刪除使用者 '{db_user.name}' (ID: {google_id})，因為該使用者尚有關聯的車籍、預約或訂單紀錄。")

    db.delete(db_user)
    db.commit()
    return True


# =================================================================
# Product CRUD (商品相關)
# =================================================================

def get_product(db: Session, product_id: int):
    """
    根據 ID 獲取單一商品。
    """
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    """
    獲取商品列表，支援分頁。
    """
    return db.query(models.Product).order_by(models.Product.id).offset(skip).limit(limit).all()

def create_product(db: Session, product: ProductCreate):
    """
    建立新商品。
    """
    # 使用 **product.dict() 可以快速地將 Pydantic 模型解包成關鍵字參數
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product_update: ProductUpdate):
    """
    根據 ID 更新商品資訊。
    """
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    # exclude_unset=True 表示只取有被前端明確給定的值
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
        
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    """
    根據 ID 刪除商品。
    """
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

# =================================================================
# WorkOrder CRUD (工單相關)
# =================================================================

from schemas.work_order import WorkOrderCreate, WorkOrderUpdate
from datetime import datetime

def get_work_order(db: Session, work_order_id: int):
    """
    根據 ID 獲取單一工單及其所有項目。
    """
    # SQLAlchemy 會自動處理 relationship，當我們查詢 WorkOrder 時，
    # 它關聯的 items 也會被載入 (因為 Pydantic schema 有宣告)。
    return db.query(models.WorkOrder).filter(models.WorkOrder.id == work_order_id).first()

def get_work_orders(db: Session, skip: int = 0, limit: int = 10):
    """
    獲取工單列表，支援分頁。預設按ID倒序，讓最新的在最前面。
    """
    return db.query(models.WorkOrder).order_by(models.WorkOrder.id.desc()).offset(skip).limit(limit).all()

def create_work_order(db: Session, work_order: WorkOrderCreate):
    """
    建立一張新的工單，這是一個比較複雜的操作，包含了：
    1. 檢查所有工單項目的商品庫存是否足夠。
    2. 根據當前商品價格計算總金額。
    3. 建立工單主記錄 (WorkOrder)。
    4. 建立所有工單項目記錄 (WorkOrderItem)。
    5. 扣除所用商品的庫存。
    這整個過程應該在一個資料庫事務 (transaction) 中完成。
    """
    
    total_amount = 0
    db_items = []

    # 步驟 1 & 2: 遍歷所有傳入的工單項目，檢查庫存並計算價格
    for item_in in work_order.items:
        db_product = get_product(db, product_id=item_in.product_id)
        
        # 如果找不到商品或庫存不足，則無法建立工單
        if not db_product:
            raise ValueError(f"找不到ID為 {item_in.product_id} 的商品")
        if db_product.stock < item_in.quantity:
            raise ValueError(f"商品 '{db_product.name}' (ID: {item_in.product_id}) 庫存不足。需要 {item_in.quantity}，但只有 {db_product.stock}。")

        # 從商品資料庫獲取當前單價，而不是信任前端傳來的價格
        unit_price = db_product.price
        total_amount += unit_price * item_in.quantity

        # 步驟 5: 扣除庫存
        db_product.stock -= item_in.quantity
        db.add(db_product)

        # 準備要寫入資料庫的 WorkOrderItem 物件
        db_item = models.WorkOrderItem(
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=unit_price
        )
        db_items.append(db_item)

    # 步驟 3: 建立工單主記錄
    db_work_order = models.WorkOrder(
        booking_id=work_order.booking_id,
        notes=work_order.notes,
        total_amount=total_amount,
        items=db_items  # 步驟 4: 將準備好的工單項目關聯到主記錄上
    )

    # 將所有變更加入到 session
    db.add(db_work_order)
    # 一次性提交所有變更 (包括庫存減少、工單建立、工單項目建立)
    db.commit()
    # 刷新 db_work_order 物件，以獲取資料庫生成的 id 和時間等資訊
    db.refresh(db_work_order)
    
    return db_work_order

def update_work_order(db: Session, work_order_id: int, work_order_update: WorkOrderUpdate):
    """
    更新工單資訊，主要用於更新狀態 (例如 '處理中' -> '已完成') 或備註。
    """
    db_work_order = get_work_order(db, work_order_id)
    if not db_work_order:
        return None

    # 使用 Pydantic 的 dict(exclude_unset=True) 來獲取前端有明確提供的欄位
    update_data = work_order_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        # 特別處理 status 的更新
        if key == "status":
            # 如果狀態被更新為「已完成」，且先前尚未設定完成時間
            if value == models.WorkOrderStatus.COMPLETED and not db_work_order.completed_at:
                db_work_order.completed_at = datetime.utcnow()
        
        setattr(db_work_order, key, value)
    
    db.add(db_work_order)
    db.commit()
    db.refresh(db_work_order)
    return db_work_order

from schemas.motor import MotorUpdate

# =================================================================
# Motor CRUD (車籍相關)
# =================================================================

def get_motor(db: Session, motor_id: int):
    """
    根據 ID 獲取單一車籍資料。
    """
    return db.query(models.Motor).filter(models.Motor.id == motor_id).first()

def update_motor(db: Session, motor_id: int, motor_update: MotorUpdate):
    """
    根據 ID 更新指定的車籍資料。
    """
    db_motor = get_motor(db, motor_id=motor_id)
    if not db_motor:
        return None
    
    # 獲取所有前端有提供的欄位值
    update_data = motor_update.dict(exclude_unset=True)
    
    # 遍歷所有要更新的欄位，並更新到資料庫物件上
    for key, value in update_data.items():
        setattr(db_motor, key, value)
        
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor

def delete_motor(db: Session, motor_id: int):
    """
    根據 ID 軟刪除指定的車籍資料。
    會將車輛的 status 設為 '已刪除'，而不是真的從資料庫移除。
    """
    db_motor = get_motor(db, motor_id=motor_id)
    if not db_motor:
        # 如果找不到，可以直接回傳 None，讓 endpoint 處理 404
        return None 
    
    # 執行軟刪除
    db_motor.status = "已刪除"
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor



# =================================================================
# Booking CRUD (預約單相關)
# =================================================================

from schemas.booking import BookingCreate, BookingUpdate

def get_booking(db: Session, booking_id: int):
    """
    根據 ID 獲取單一預約單。
    """
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()

def get_bookings(db: Session, skip: int = 0, limit: int = 100, date_str: str = None):
    """
    獲取預約單列表，支援分頁與日期篩選。預設按預約時間倒序排列。
    """
    query = db.query(models.Booking)
    if date_str:
        from datetime import datetime, timedelta
        try:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            query = query.filter(models.Booking.booking_time >= start_date, models.Booking.booking_time < end_date)
        except ValueError:
            pass
    return query.order_by(models.Booking.booking_time.desc()).offset(skip).limit(limit).all()

from datetime import datetime, timedelta

def get_bookings_by_date(db: Session, date_str: str):
    """
    獲取特定日期的預約單列表
    date_str 格式為 'YYYY-MM-DD'
    """
    try:
        start_date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        
        return db.query(models.Booking).filter(
            models.Booking.booking_time >= start_date,
            models.Booking.booking_time < end_date,
            models.Booking.status.in_([models.BookingStatus.PENDING, models.BookingStatus.SYSTEM_CLOSED])
        ).all()
    except ValueError:
        raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD")

def create_booking(db: Session, booking: BookingCreate, force: bool = False, is_system_close: bool = False):
    """
    建立一筆新的預約紀錄。
    在建立前會進行驗證，確保使用者和車籍資料存在且匹配。
    """
    # 驗證使用者是否存在
    db_user = get_user(db, google_id=booking.google_id)
    if not db_user:
        raise ValueError(f"找不到 Google ID 為 '{booking.google_id}' 的使用者。")

    # 驗證車籍資料是否存在
    db_motor = get_motor(db, motor_id=booking.motor_id)
    if not db_motor:
        raise ValueError(f"找不到 ID 為 {booking.motor_id} 的車籍資料。")

    # 驗證該車輛是否屬於該使用者
    if db_motor.google_id != db_user.google_id:
        raise ValueError(f"車籍資料 (ID: {booking.motor_id}) 與使用者 (Google ID: {booking.google_id}) 不匹配。")

    # 若非強制寫入，需檢查該時段是否已滿或被關閉
    if not force:
        existing_booking = db.query(models.Booking).filter(
            models.Booking.booking_time == booking.booking_time,
            models.Booking.status.in_([models.BookingStatus.PENDING, models.BookingStatus.SYSTEM_CLOSED])
        ).first()
        if existing_booking:
            if existing_booking.status == models.BookingStatus.SYSTEM_CLOSED:
                raise ValueError(f"您選擇的時段目前為不開放。")
            else:
                raise ValueError(f"您選擇的時段已被預約，請選擇其他時段。")

    # 提供如果是系統關閉的狀態設定
    new_status = models.BookingStatus.SYSTEM_CLOSED if is_system_close else models.BookingStatus.PENDING

    # 移除傳入 model 的額外屬性（如 AdminBookingCreate 帶進來的 force）
    booking_dict = booking.dict()
    if 'force' in booking_dict:
        del booking_dict['force']

    # 將 Pydantic 模型轉換為 SQLAlchemy 模型，並設定狀態
    db_booking = models.Booking(
        **booking_dict,
        status=new_status
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def update_booking(db: Session, booking_id: int, booking_update: BookingUpdate):
    """
    更新預約單資訊，主要用於更新狀態或備註。
    """
    db_booking = get_booking(db, booking_id=booking_id)
    if not db_booking:
        return None

    # 獲取有被前端明確給定的值
    update_data = booking_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_booking, key, value)

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking