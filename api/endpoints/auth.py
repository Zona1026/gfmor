from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from db import crud, database
from schemas.user import UserCreate, User
from schemas.token import GoogleToken, LoginResponse
from core.config import settings
from core import security

# For Google Auth
from google.oauth2 import id_token
from google.auth.transport import requests

router = APIRouter()

GOOGLE_CLIENT_ID = "357528958616-1mbtrri5ii7irbqpftd8ml3qtdr7ho0u.apps.googleusercontent.com"

@router.post("/google", response_model=LoginResponse)
async def login_with_google(google_token: GoogleToken, db: Session = Depends(database.get_db)):
    print("=== [AUTH] 收到 Google 登入請求 ===")
    try:
        # 驗證從前端傳來的 Google ID Token
        print(f"[AUTH] 正在驗證 Google Token (長度: {len(google_token.token)})...")
        idinfo = id_token.verify_oauth2_token(
            google_token.token, requests.Request(), GOOGLE_CLIENT_ID, clock_skew_in_seconds=10
        )
        print(f"[AUTH] Google Token 驗證成功!")

        # 從 token 中提取使用者資訊
        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name")
        print(f"[AUTH] 使用者資訊: google_id={google_id}, email={email}, name={name}")

        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無法從 Google Token 中獲取有效的 Email 或 Google ID",
            )

        # 檢查使用者是否已存在於我們的資料庫
        user = crud.get_user(db, google_id=google_id)
        if not user:
            # 若 Google ID 找不到，嘗試用 Email 尋找 (處理早期無 Google ID 或測試資料的情況)
            user = crud.get_user_by_email(db, email=email)
            print(f"[AUTH] 透過 Email 查詢結果: user={'存在' if user else '不存在'}")
            
        print(f"[AUTH] 資料庫查詢結果: user={'存在' if user else '不存在'}")

        if not user:
            # 如果使用者不存在，則建立新使用者
            print(f"[AUTH] 正在建立新使用者...")
            user_in = UserCreate(google_id=google_id, email=email, name=name)
            user = crud.create_user(db=db, user=user_in)
            print(f"[AUTH] 新使用者建立成功!")

        # 建立我們自己系統的 Access Token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user.google_id}, expires_delta=access_token_expires
        )
        print(f"[AUTH] Access Token 建立成功!")

        # 在回傳的資料中，除了 token，也可以額外附加使用者資訊
        # 這裡我們回傳一個符合 Token schema 的物件
        result = {"access_token": access_token, "token_type": "bearer", "user": user}
        print(f"[AUTH] 登入流程完成，準備回傳結果")
        return result

    except ValueError as e:
        # 如果 token 無效 (例如過期、簽名不符等)
        print(f"[AUTH] ValueError: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"無效的 Google Token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        # 處理其他可能的錯誤
        import traceback
        print(f"[AUTH] Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"伺服器內部錯誤: {e}",
        )
