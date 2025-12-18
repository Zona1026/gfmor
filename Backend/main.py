# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import models, database, schemas, crud
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import shutil
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, Form


# 自動建立資料庫表 (包含新加的 SlotConfiguration)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 設定 CORS (保持你的設定)
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello! 前端連線成功！"}

@app.get("/admin")
def read_admin():
    return RedirectResponse(url="/static/admin.html")

# GOOGLE_CLIENT_ID 請填入你自己的
GOOGLE_CLIENT_ID = "357528958616-1mbtrri5ii7irbqpftd8ml3qtdr7ho0u.apps.googleusercontent.com"

# --- 原有的 Google 登入 API (保持不變) ---
@app.post("/auth/google")
def google_login(request: schemas.GoogleLoginRequest, db: Session = Depends(database.get_db)):
    token = request.token

    try:
        # 嘗試驗證 Token
        # ★★★ 修改這裡：把 10 改成 60 ★★★
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60  # 允許 60 秒的時間誤差
        )
        google_user_id = id_info['sub']
        email = id_info['email']
        name = id_info.get('name', 'Unknown')
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google Token: {str(e)}")

    user = crud.get_user_by_google_id(db, google_id=google_user_id)

    if not user:
        user_data = {"sub": google_user_id, "email": email, "name": name}
        user = crud.create_google_user(db, user_data)
        
    if not user.phone:
        return {
            "action": "FILL_PHONE",
            "message": "請補填電話號碼",
            "google_id": user.google_id,
            "user_name": user.name
        }
    else:
        return {
            "action": "GO_HOME",
            "message": "登入成功",
            "user": {
                "google_id": user.google_id,
                "name": user.name, 
                "phone": user.phone
            }
        }

# --- 原有的更新電話 API (保持不變) ---
@app.put("/users/update-phone")
def update_phone(request: schemas.PhoneUpdateRequest, db: Session = Depends(database.get_db)):
    user = crud.get_user_by_google_id(db, google_id=request.google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.phone = request.phone
    db.commit()
    return {"message": "電話更新成功", "action": "GO_HOME"}

# --- 原有的取得個資 API (保持不變) ---
@app.get("/users/{google_id}")
def read_user_profile(google_id: str, db: Session = Depends(database.get_db)):
    user = crud.get_user_by_google_id(db, google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "google_id": user.google_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "created_at": user.created_at
    }

# --- 原有的管理員登入 API (保持不變) ---
class AdminLoginRequest(BaseModel):
    account: int 
    password: str

@app.post("/admin/login")
def admin_login(request: AdminLoginRequest, db: Session = Depends(database.get_db)):
    admin = db.query(models.Admin).filter(
        models.Admin.account_id == request.account,
        models.Admin.password == request.password
    ).first()

    if not admin:
        raise HTTPException(status_code=401, detail="登入失敗")
    
    return {
        "message": "管理員登入成功",
        "user": {
            "name": admin.name,
            "role": admin.role,
            "account": admin.account_id
        }
    }

# ========================================================
#  【新增功能區】: 預約系統邏輯 Given-When-Then 實作
# ========================================================

# 1. 使用者建立預約
@app.post("/bookings", response_model=schemas.BookingResponse)
def create_booking(booking_data: schemas.BookingCreate, db: Session = Depends(database.get_db)):
    
    # --- 新增：營業時間檢查 ---
    req_time = booking_data.booking_time
    day_of_week = req_time.weekday() # 0=週一, 5=週六, 6=週日
    hour = req_time.hour
    minute = req_time.minute

    # 1. 檢查分鐘數 (必須是整點)
    if minute != 0:
         raise HTTPException(status_code=400, detail="僅接受整點預約 (例如 13:00)")

    # 2. 檢查週日公休
    if day_of_week == 6:
        raise HTTPException(status_code=400, detail="抱歉，週日公休")

    # 3. 檢查營業時段
    # 週六: 11:00 - 21:00
    if day_of_week == 5:
        if not (11 <= hour <= 21):
            raise HTTPException(status_code=400, detail="週六營業時間為 11:00 - 21:00")
            
    # 平日 (週一至週五): 13:00 - 21:00
    else:
        if not (13 <= hour <= 21):
            raise HTTPException(status_code=400, detail="平日營業時間為 13:00 - 21:00")

    # --- 以下是原本的容量檢查與建立訂單邏輯 (保持不變) ---
    
    # A. 檢查容量
    slot_config = db.query(models.SlotConfiguration).filter(
        models.SlotConfiguration.target_time == booking_data.booking_time
    ).first()
    
    limit = slot_config.max_capacity if slot_config else 1
    
    current_count = db.query(models.Booking).filter(
        models.Booking.booking_time == booking_data.booking_time,
        models.Booking.status != "預約取消"
    ).count()
    
    # B. 判斷是否額滿
    if current_count >= limit:
        raise HTTPException(
            status_code=400,
            detail=f"此時段已額滿，無法預約 (上限: {limit} 人)"
        )
    
    # C. 寫入資料庫
    new_booking = models.Booking(
        user_google_id=booking_data.user_google_id,
        car_model=booking_data.car_model,
        booking_time=booking_data.booking_time,
        category=booking_data.category,
        engine_no=booking_data.engine_no,
        note=booking_data.note,
        status="預約中"
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    return new_booking

# 2. 使用者查看自己的預約紀錄
@app.get("/my-bookings/{google_id}", response_model=List[schemas.BookingResponse])
def get_my_bookings(google_id: str, db: Session = Depends(database.get_db)):
    bookings = db.query(models.Booking).filter(
        models.Booking.user_google_id == google_id
    ).order_by(models.Booking.booking_time.desc()).all()
    
    return bookings

# 3. 管理員查看所有預約 (Admin Only)
@app.get("/admin/bookings", response_model=List[schemas.BookingResponse])
def get_all_bookings(db: Session = Depends(database.get_db)):
    # 註: 正式上線建議這裡要加 header 驗證是否為 admin，目前先開放方便測試
    return db.query(models.Booking).order_by(models.Booking.booking_time.desc()).all()

# 4. 管理員調整時段容量 (開放第二人)
@app.post("/admin/slots/capacity", response_model=schemas.SlotConfigResponse)
def set_slot_capacity(config: schemas.SlotConfigCreate, db: Session = Depends(database.get_db)):
    """
    管理員用這個 API 來指定某個時間點可以接 2 個客人
    JSON Body: { "target_time": "2025-12-14 10:00:00", "max_capacity": 2 }
    """
    # 檢查該時段是否已有設定
    existing = db.query(models.SlotConfiguration).filter(
        models.SlotConfiguration.target_time == config.target_time
    ).first()

    if existing:
        # 更新
        existing.max_capacity = config.max_capacity
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 新增
        new_config = models.SlotConfiguration(
            target_time=config.target_time,
            max_capacity=config.max_capacity
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return new_config
    

# 1. 取得個人的消費紀錄
@app.get("/my-consumptions/{google_id}", response_model=List[schemas.ConsumptionResponse])
def get_my_consumptions(google_id: str, db: Session = Depends(database.get_db)):
    return db.query(models.Consumption).filter(
        models.Consumption.user_google_id == google_id
    ).order_by(models.Consumption.created_at.desc()).all()

# 2. (管理員用) 新增消費紀錄 & 自動升級邏輯
# main.py (找到 add_consumption 函式並修改中間一段)

@app.post("/admin/consumptions")
def add_consumption(data: schemas.CreateConsumption, db: Session = Depends(database.get_db)):
    # ... (前面記錄消費的代碼不用變) ...
    new_record = models.Consumption(
        user_google_id=data.user_google_id,
        amount=data.amount,
        description=data.description
    )
    db.add(new_record)
    
    # B. 更新使用者累積金額
    user = db.query(models.User).filter(models.User.google_id == data.user_google_id).first()
    if user:
        user.total_spending += data.amount
        
        # ★★★ C. 新的自動升級邏輯 (關鍵修改) ★★★
        current_total = user.total_spending
        
        if current_total > 500000:
            user.level = "爆改車主之SVIP"
        elif current_total > 300000:
            user.level = "爆改車主之VVIP"
        elif current_total > 100000:
            user.level = "爆改車主"
        elif current_total > 50000:
            user.level = "大改車主"
        else:
            user.level = "一般會員"
            
    db.commit()
    return {"message": "消費登錄成功", "current_level": user.level, "total_spent": user.total_spending}

# 別忘了修改 user profile 接口，讓它回傳 level 和 total_spending
@app.get("/users/{google_id}")
def read_user_profile(google_id: str, db: Session = Depends(database.get_db)):
    user = crud.get_user_by_google_id(db, google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "google_id": user.google_id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "created_at": user.created_at,
        # 新增回傳這兩個欄位
        "level": user.level,
        "total_spending": user.total_spending
    }

@app.get("/portfolio")
def get_portfolio_items(db: Session = Depends(database.get_db)):
    return db.query(models.PortfolioItem).order_by(models.PortfolioItem.created_at.desc()).all()

# 上傳作品 (限管理員)
# 注意：這裡用 Form(...) 和 File(...) 是因為要同時傳文字和檔案
@app.post("/admin/portfolio/upload")
def upload_portfolio_item(
    title: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    # 1. 確保資料夾存在
    upload_dir = "static/uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # 2. 儲存檔案 (為了避免檔名重複，建議加個時間戳，這裡先簡化直接存)
    # 或是你可以用 uuid 改名，這裡示範用原始檔名
    file_location = f"{upload_dir}/{file.filename}"
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. 寫入資料庫 (存的是網址路徑 /static/uploads/...)
    db_url = f"/static/uploads/{file.filename}"
    
    new_item = models.PortfolioItem(
        title=title,
        category=category,
        image_url=db_url
    )
    db.add(new_item)
    db.commit()
    
    return {"message": "上傳成功", "url": db_url}

# 刪除作品 (限管理員)
@app.delete("/admin/portfolio/{item_id}")
def delete_portfolio_item(item_id: int, db: Session = Depends(database.get_db)):
    item = db.query(models.PortfolioItem).filter(models.PortfolioItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="找不到該作品")
    
    # (選擇性) 這裡也可以順便把實體檔案刪除 os.remove(...)
    
    db.delete(item)
    db.commit()
    return {"message": "刪除成功"}