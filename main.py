from fastapi import FastAPI

# 建立 FastAPI 應用程式實例
app = FastAPI(
    title="GFmotor API",
    description="GFmotor 改車系統的後端 API。",
    version="0.1.0"
)

# 根目錄 API，用於快速測試服務是否正常運行
@app.get("/")
def read_root():
    """
    根目錄，回傳一個歡迎訊息。
    """
    return {"message": "歡迎來到 GFmotor API！"}

# 在這裡，我們未來將會引入由 api/router.py 定義的路由
# from api.router import api_router
# app.include_router(api_router, prefix="/api/v1")
