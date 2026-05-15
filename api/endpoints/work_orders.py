# 引入 FastAPI 和相關模組
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# 引入資料庫 CRUD 函式、schemas 和資料庫 session 管理
from db import crud
from schemas import work_order as work_order_schema
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
    FastAPI 的 Depends() 會幫我們處理這一切。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================================================================
# API Endpoints
# =================================================================

@router.post(
    "/", 
    response_model=work_order_schema.WorkOrder, 
    status_code=status.HTTP_201_CREATED,
    summary="建立新工單"
)
def create_work_order(work_order: work_order_schema.WorkOrderCreate, db: Session = Depends(get_db)):
    """
    建立一張新的工單，這會是系統中的一個核心操作。

    - **booking_id**: 此工單對應的預約單 ID (必填)。
    - **notes**: 關於此工單的內部備註 (選填)。
    - **items**: 一個列表，包含此工單所有要用到的商品項目 (必填):
        - **product_id**: 商品 ID (必填)。
        - **quantity**: 使用數量 (必填)。

    **注意**: 後端會自動檢查庫存並計算總金額，如果任何一項商品庫存不足，
    請求將會失敗並回傳 400 錯誤。
    """
    try:
        # 呼叫 CRUD 層的函式來執行建立工單的複雜邏輯
        return crud.create_work_order(db=db, work_order=work_order)
    except ValueError as e:
        # 如果 CRUD 層在檢查庫存或處理資料時發現問題，會拋出 ValueError。
        # 我們在這裡捕捉這個錯誤，並回傳一個 HTTP 400 錯誤給客戶端。
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[work_order_schema.WorkOrder], summary="讀取工單列表")
def read_work_orders(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    讀取資料庫中的工單列表，預設按建立時間由新到舊排序。
    可使用 `skip` 和 `limit` 參數來進行分頁。
    """
    work_orders = crud.get_work_orders(db, skip=skip, limit=limit)
    return work_orders

@router.get("/{work_order_id}", response_model=work_order_schema.WorkOrder, summary="讀取單一工單")
def read_work_order(work_order_id: int, db: Session = Depends(get_db)):
    """
    根據工單 `work_order_id` 讀取單一工單的詳細資料，包含所有工單項目。
    """
    db_work_order = crud.get_work_order(db, work_order_id=work_order_id)
    if db_work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
    return db_work_order

@router.put("/{work_order_id}", response_model=work_order_schema.WorkOrder, summary="更新工單狀態或備註")
def update_work_order(
    work_order_id: int, 
    work_order: work_order_schema.WorkOrderUpdate, 
    db: Session = Depends(get_db)
):
    """
    根據工單 `work_order_id` 更新其資訊。
    主要用於變更工單狀態 (例如：'處理中' -> '已完成') 或修改內部備註。
    """
    db_work_order = crud.update_work_order(db, work_order_id=work_order_id, work_order_update=work_order)
    if db_work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
    return db_work_order
