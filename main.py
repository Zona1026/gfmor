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

@app.on_event("startup")
def on_startup():
    """應用啟動時，自動檢查並建立/遷移資料表"""
    from sqlalchemy import text, inspect
    from db.database import engine
    from db.models import Base
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # 針對 portfolio_items：若存在舊版中文欄位，先刪除再重建
        if "portfolio_items" in existing_tables:
            columns = [col["name"] for col in inspector.get_columns("portfolio_items")]
            if "標題" in columns or "title" not in columns:
                # 舊版中文欄位的表，需要遷移
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS portfolio_items"))
                    conn.commit()
                print("[Startup] 已刪除舊版 portfolio_items 表，將重新建立")
        
        # 建立所有不存在的表（包括剛刪除的 portfolio_items）
        Base.metadata.create_all(bind=engine)
        print("[Startup] 資料表檢查完成")
    except Exception as e:
        print(f"[Startup] 資料表初始化警告: {e}")

# 引入由 api/router.py 定義的路由
from api.router import api_router

# 將 api_router 掛載到應用程式上，並設定前綴為 /api
# 未來所有的 API 都會是 /api/products, /api/users 這樣的形式
app.include_router(api_router, prefix="/api")
