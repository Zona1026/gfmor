# 引入 FastAPI 和相關模組
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

import time
import os
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, File

cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
  api_key = os.getenv('CLOUDINARY_API_KEY'),
  api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

# 引入資料庫 CRUD 函式、schemas 和資料庫 session 管理
from db import crud
from schemas import user as user_schema
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

@router.post("/", response_model=user_schema.User, summary="建立測試用使用者")
def create_test_user(user: user_schema.TestUserCreate, db: Session = Depends(get_db)):
    """
    建立一筆新的「測試用」使用者。
    後端會自動產生一組假的 google_id。
    如果 Email 已存在，將會回傳錯誤。

    - **name**: 使用者姓名 (必填)
    - **email**: 使用者 Email (必填)
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")
    
    # 產生一組基於時間的假 Google ID
    fake_google_id = f"test-user-{int(time.time())}"
    
    # 組合出一個完整的 UserCreate 模型物件
    user_to_create = user_schema.UserCreate(google_id=fake_google_id, **user.dict())
    
    return crud.create_user(db=db, user=user_to_create)


@router.get(
    "/search",
    response_model=List[user_schema.UserWithMotors],
    summary="依姓名模糊搜尋客戶"
)
def search_users_by_name(
    name: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    根據使用者姓名進行模糊搜尋，回傳符合條件的使用者列表，
    以及他們名下的車籍資料。

    - **name**: 要搜尋的姓名關鍵字。
    """
    if not name:
        return []
    users = crud.get_users_by_name(db, name=name, skip=skip, limit=limit)
    return users

@router.get("/", response_model=List[user_schema.User], summary="讀取使用者列表")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    讀取資料庫中的使用者列表。
    可使用 `skip` 和 `limit` 參數來進行分頁。
    """
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{google_id}", response_model=user_schema.UserWithMotors, summary="讀取單一使用者(含車籍)")
def read_user(google_id: str, db: Session = Depends(get_db)):
    """
    根據 `google_id` 讀取單一使用者的詳細資料，包含其名下的所有車輛。
    """
    db_user = crud.get_user(db, google_id=google_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="找不到該使用者")
    return db_user

@router.put("/{google_id}", response_model=user_schema.User, summary="更新使用者資訊")
def update_user(
    google_id: str,
    user: user_schema.UserUpdate,
    db: Session = Depends(get_db)
):
    """
    根據 `google_id` 更新該使用者的資訊 (例如：姓名、電話、會員等級)。
    """
    try:
        db_user = crud.update_user(db, google_id=google_id, user_update=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    if db_user is None:
        raise HTTPException(status_code=404, detail="找不到該使用者")
    return db_user

@router.delete("/{google_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除使用者")
def delete_user(google_id: str, db: Session = Depends(get_db)):
    """
    根據 `google_id` 刪除使用者。
    注意：如果該使用者尚有關聯的車籍、預約或訂單紀錄，系統將不允許刪除，並會回傳錯誤訊息。
    """
    try:
        crud.delete_user(db, google_id=google_id)
    except ValueError as e:
        # 捕捉 CRUD 層拋出的 ValueError，並以 400 狀態碼回傳
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    # 成功刪除時，回傳 204 No Content，不需要 body
    return

@router.post("/{google_id}/avatar", response_model=user_schema.User, summary="上傳使用者頭像")
def upload_avatar(
    google_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上傳使用者頭像至 Cloudinary 並更新資料庫紀錄。
    """
    # 先確認使用者存在
    db_user = crud.get_user(db, google_id=google_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="找不到該使用者")
        
    try:
        # 上傳到 Cloudinary
        result = cloudinary.uploader.upload(file.file)
        url = result.get("secure_url")
        
        # 更新資料庫
        user_update = user_schema.UserUpdate(avatar=url)
        updated_user = crud.update_user(db, google_id=google_id, user_update=user_update)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"圖片上傳失敗: {str(e)}")
