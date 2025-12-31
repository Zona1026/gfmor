# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from . import models, database, schemas, crud
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
import shutil
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, Form


# 自動建立資料庫表 (包含新加的 SlotConfiguration)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Construct path to static directory relative to this file
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 設定 CORS
# 從環境變數讀取允許的來源，如果未設定，則使用本地開發的預設值
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500")
origins = [origin.strip() for origin in cors_origins_str.split(',')]

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

# 從環境變數讀取 GOOGLE_CLIENT_ID，若未設定則使用預設值
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "357528958616-1mbtrri5ii7irbqpftd8ml3qtdr7ho0u.apps.googleusercontent.com")

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

# --- User Profile Update ---
@app.put("/users/{google_id}/profile", response_model=schemas.User)
def update_user_profile(google_id: str, request: schemas.UserUpdateRequest, db: Session = Depends(database.get_db)):
    """
    更新使用者資料 (姓名、電話)
    """
    user = crud.update_user(db, google_id=google_id, user_update=request)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



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

    # 產生一個簡單的 session token
    session_token = str(uuid.uuid4())
    
    return {
        "message": "管理員登入成功",
        "token": session_token, # 將 token 回傳給前端
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
    

# ========================================================
#  作品集 (Portfolio) API
# ========================================================
from fastapi import Header, File, UploadFile, Form
import uuid
import os
import shutil
from typing import Optional

# 簡易的 token 驗證
async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="無效的認證標頭")
    # 在一個真正的應用中，你會在這裡解碼和驗證 JWT
    # 但根據目前的登入邏輯，我們只檢查 token 是否存在
    token = authorization.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="未提供 Token")
    return token

# --- Public Endpoint ---

@app.get("/api/portfolios", response_model=List[schemas.PortfolioItem])
def read_portfolio_items(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    公開的 API，獲取所有作品集項目列表。
    """
    items = crud.get_portfolio_items(db, skip=skip, limit=limit)
    return items

# --- Admin-only Endpoints ---

@app.post("/api/portfolios", response_model=schemas.PortfolioItem, status_code=status.HTTP_201_CREATED)
def create_portfolio_item(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    token: str = Depends(verify_token)
):
    """
    (管理員) 建立一個新的作品集項目。
    """
    try:
        upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # 產生獨一無二的檔名
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_location = os.path.join(upload_dir, unique_filename)

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"/static/uploads/{unique_filename}"
        
        return crud.create_portfolio_item(db=db, title=title, description=description, category=category, image_url=image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立作品時發生錯誤: {str(e)}")

@app.get("/api/portfolios/{item_id}", response_model=schemas.PortfolioItem)
def read_portfolio_item(item_id: int, db: Session = Depends(database.get_db), token: str = Depends(verify_token)):
    """
    (管理員) 獲取單一作品集項目的詳細資訊。
    """
    db_item = crud.get_portfolio_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="找不到該作品")
    return db_item

@app.put("/api/portfolios/{item_id}", response_model=schemas.PortfolioItem)
def update_portfolio_item(
    item_id: int,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    token: str = Depends(verify_token)
):
    """
    (管理員) 更新一個現有的作品集項目。
    """
    try:
        db_item = crud.get_portfolio_item(db, item_id=item_id)
        if not db_item:
            raise HTTPException(status_code=404, detail="找不到該作品")

        image_url = db_item.image_url
        
        if file:
            # 如果有新檔案上傳，則刪除舊檔案並儲存新檔案
            old_image_path_relative = db_item.image_url.lstrip('/')
            old_image_path_full = os.path.join(os.path.dirname(__file__), old_image_path_relative)
            if os.path.exists(old_image_path_full):
                os.remove(old_image_path_full)

            upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_location = os.path.join(upload_dir, unique_filename)

            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            image_url = f"/static/uploads/{unique_filename}"

        updated_item = crud.update_portfolio_item(
            db=db, item_id=item_id, title=title, description=description, category=category, image_url=image_url if file else None
        )
        return updated_item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新作品時發生錯誤: {str(e)}")


@app.delete("/api/portfolios/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(item_id: int, db: Session = Depends(database.get_db), token: str = Depends(verify_token)):
    """
    (管理員) 刪除一個作品集項目。
    """
    image_url_to_delete = crud.delete_portfolio_item(db, item_id=item_id)

    if image_url_to_delete is None:
        raise HTTPException(status_code=404, detail="找不到該作品")

    # 從檔案系統中刪除圖片檔案
    # 將 URL 路徑轉換為檔案系統路徑
    image_path_relative = image_url_to_delete.lstrip('/')
    image_path_full = os.path.join(os.path.dirname(__file__), image_path_relative)
    
    if os.path.exists(image_path_full):
        os.remove(image_path_full)
    
    return