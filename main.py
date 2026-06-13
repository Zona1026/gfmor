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

    def migrate_guest_orders(conn, inspector):
        if "orders" not in inspector.get_table_names():
            return

        columns = inspector.get_columns("orders")
        column_names = [col["name"] for col in columns]

        if "guest_customer_id" not in column_names:
            conn.execute(text("ALTER TABLE orders ADD COLUMN guest_customer_id INTEGER NULL"))
            conn.commit()
            print("[Startup] 已新增 orders.guest_customer_id 欄位")

        google_id_col = next((col for col in columns if col["name"] == "google_id"), None)
        if not google_id_col or not google_id_col.get("nullable", True):
            dialect = engine.dialect.name
            if dialect in ("mysql", "mariadb"):
                conn.execute(text("ALTER TABLE orders MODIFY google_id VARCHAR(255) NULL"))
                conn.commit()
                print("[Startup] 已調整 orders.google_id 為可空值")
            elif dialect == "sqlite":
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS orders_new (
                        id INTEGER PRIMARY KEY,
                        google_id VARCHAR(255) NULL,
                        guest_customer_id INTEGER NULL,
                        status VARCHAR(12) NOT NULL,
                        source VARCHAR(20) NOT NULL DEFAULT 'online',
                        total_amount INTEGER NOT NULL,
                        recipient_name VARCHAR(50) NOT NULL,
                        recipient_phone VARCHAR(20) NOT NULL,
                        shipping_address VARCHAR(255) NOT NULL,
                        notes TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(google_id) REFERENCES users("Google ID"),
                        FOREIGN KEY(guest_customer_id) REFERENCES guest_customers(id)
                    )
                """))
                conn.execute(text("""
                    INSERT INTO orders_new (
                        id, google_id, guest_customer_id, status, source, total_amount,
                        recipient_name, recipient_phone, shipping_address, notes, created_at, updated_at
                    )
                    SELECT
                        id, google_id, guest_customer_id, status, source, total_amount,
                        recipient_name, recipient_phone, shipping_address, notes, created_at, updated_at
                    FROM orders
                """))
                conn.execute(text("DROP TABLE orders"))
                conn.execute(text("ALTER TABLE orders_new RENAME TO orders"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_id ON orders (id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orders_guest_customer_id ON orders (guest_customer_id)"))
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
                print("[Startup] 已重建 SQLite orders 表以支援散客訂單")

    def migrate_order_item_status(conn, inspector):
        if "order_items" not in inspector.get_table_names():
            return

        columns = [col["name"] for col in inspector.get_columns("order_items")]
        if "status" in columns:
            return

        dialect = engine.dialect.name
        if dialect in ("mysql", "mariadb"):
            conn.execute(text("""
                ALTER TABLE order_items
                ADD COLUMN status ENUM(
                    'NOT_ORDERED',
                    'ORDERED',
                    'ARRIVED_NEED_NOTIFY',
                    'NOTIFIED',
                    'COMPLETED'
                ) NOT NULL DEFAULT 'NOT_ORDERED'
            """))
        else:
            conn.execute(text("ALTER TABLE order_items ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'NOT_ORDERED'"))

        conn.commit()
        print("[Startup] 已新增 order_items.status 欄位")
    
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
        with engine.connect() as conn:
            inspector = inspect(engine)
            migrate_guest_orders(conn, inspector)
            inspector = inspect(engine)
            migrate_order_item_status(conn, inspector)
        print("[Startup] 資料表檢查完成")
    except Exception as e:
        print(f"[Startup] 資料表初始化警告: {e}")

# 引入由 api/router.py 定義的路由
from api.router import api_router

# 將 api_router 掛載到應用程式上，並設定前綴為 /api
# 未來所有的 API 都會是 /api/products, /api/users 這樣的形式
app.include_router(api_router, prefix="/api")
