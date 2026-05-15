from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 建立 FastAPI 應用程式實例
app = FastAPI(
    title="GFmotor API",
    description="GFmotor 改車系統的後端 API。",
    version="0.1.0"
)

# CORS 設定：允許前端 (localhost:5173 以及上線後的網域) 跨域請求
import os
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        frontend_url
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態檔案目錄
# 這會讓 http://127.0.0.1:8000/test/index.html 可以存取到 static/index.html
app.mount("/test", StaticFiles(directory="static"), name="static")

# 根目錄 API，用於快速測試服務是否正常運行
@app.get("/")
def read_root():
    """
    根目錄，回傳一個歡迎訊息。
    """
    return {"message": "歡迎來到 GFmotor API！"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/debug/test-login")
def debug_test_login():
    """臨時除錯用端點，測試登入相關模組是否正常"""
    results = {}
    try:
        from core.security import verify_password, get_password_hash
        results["passlib_import"] = "OK"
    except Exception as e:
        results["passlib_import"] = f"FAIL: {e}"
    
    try:
        from core.security import get_password_hash
        hashed = get_password_hash("test")
        results["hash_test"] = f"OK: {hashed[:20]}..."
    except Exception as e:
        results["hash_test"] = f"FAIL: {e}"
    
    try:
        from core.security import verify_password, get_password_hash
        hashed = get_password_hash("12345")
        result = verify_password("12345", hashed)
        results["verify_test"] = f"OK: {result}"
    except Exception as e:
        results["verify_test"] = f"FAIL: {e}"
    
    try:
        from db.database import SessionLocal
        from db import models
        db = SessionLocal()
        admin = db.query(models.Admin).filter(models.Admin.username == "12345").first()
        if admin:
            results["db_admin_exists"] = f"OK: username={admin.username}, has_password={bool(admin.hashed_password)}"
            try:
                result = verify_password("12345", admin.hashed_password)
                results["db_verify"] = f"OK: {result}"
            except Exception as e:
                results["db_verify"] = f"FAIL: {e}"
        else:
            results["db_admin_exists"] = "NOT FOUND"
        db.close()
    except Exception as e:
        results["db_query"] = f"FAIL: {e}"
    
    return results

# 引入由 api/router.py 定義的路由
from api.router import api_router

# 將 api_router 掛載到應用程式上，並設定前綴為 /api
# 未來所有的 API 都會是 /api/products, /api/users 這樣的形式
app.include_router(api_router, prefix="/api")
