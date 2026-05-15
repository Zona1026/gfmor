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
        frontend_url,
        "*" # 為了測試方便先開放所有，實際上線可以限制
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

# 引入由 api/router.py 定義的路由
from api.router import api_router

# 將 api_router 掛載到應用程式上，並設定前綴為 /api
# 未來所有的 API 都會是 /api/products, /api/users 這樣的形式
app.include_router(api_router, prefix="/api")
