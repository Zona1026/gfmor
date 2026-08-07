# 引入 FastAPI 和相關模組
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Query
from sqlalchemy.orm import Session
from typing import List

# 引入資料庫 CRUD 函式、schemas 和資料庫 session 管理
from api.dependencies.admin_auth import require_admin, require_manager_admin, require_super_admin
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
def create_work_order(
    work_order: work_order_schema.WorkOrderCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
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
def read_work_orders(
    skip: int = 0,
    limit: int = 10,
    status_filter: str = Query(None, alias="status"),
    date_str: str = None,
    q: str = None,
    service_type: str = None,
    payment_status: str = None,
    responsible_staff: str = None,
    include_deleted: bool = False,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    讀取資料庫中的工單列表，預設按建立時間由新到舊排序。
    可使用 `skip` 和 `limit` 參數來進行分頁。
    """
    try:
        work_orders = crud.get_work_orders(
            db,
            skip=skip,
            limit=limit,
            status=status_filter,
            date_str=date_str,
            q=q,
            service_type=service_type,
            payment_status=payment_status,
            responsible_staff=responsible_staff,
            include_deleted=include_deleted,
        )
        return work_orders
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/approvals/", response_model=List[work_order_schema.WorkOrderApproval], summary="讀取工單主管審核列表")
def read_work_order_approvals(
    approval_status: str = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return crud.get_work_order_approvals(db, status=approval_status, skip=skip, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/approvals/{approval_id}/approve", response_model=work_order_schema.WorkOrderApproval, summary="核准工單審核")
def approve_work_order_approval(
    approval_id: int,
    review: work_order_schema.WorkOrderApprovalReview,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if not review.reviewed_by:
        review.reviewed_by = admin["username"] or admin["role"]
    try:
        db_approval = crud.review_work_order_approval(db, approval_id=approval_id, review=review, approved=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if db_approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到審核項目")
    return db_approval

@router.post("/approvals/{approval_id}/reject", response_model=work_order_schema.WorkOrderApproval, summary="退回工單審核")
def reject_work_order_approval(
    approval_id: int,
    review: work_order_schema.WorkOrderApprovalReview,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if not review.reviewed_by:
        review.reviewed_by = admin["username"] or admin["role"]
    try:
        db_approval = crud.review_work_order_approval(db, approval_id=approval_id, review=review, approved=False)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if db_approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到審核項目")
    return db_approval

@router.get("/{work_order_id}", response_model=work_order_schema.WorkOrder, summary="讀取單一工單")
def read_work_order(
    work_order_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    根據工單 `work_order_id` 讀取單一工單的詳細資料，包含所有工單項目。
    """
    db_work_order = crud.get_work_order(db, work_order_id=work_order_id)
    if db_work_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
    return db_work_order

@router.post("/{work_order_id}/line-items", response_model=work_order_schema.WorkOrder, summary="追加工單明細")
def add_work_order_line_item(
    work_order_id: int,
    item: work_order_schema.WorkOrderLineItemCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    try:
        db_work_order = crud.add_work_order_line_item(db, work_order_id=work_order_id, item=item)
        if db_work_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
        return db_work_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{work_order_id}/payments", response_model=work_order_schema.WorkOrder, summary="新增工單付款")
def add_work_order_payment(
    work_order_id: int,
    payment: work_order_schema.WorkOrderPaymentCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    try:
        db_work_order = crud.add_work_order_payment(db, work_order_id=work_order_id, payment=payment)
        if db_work_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
        return db_work_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{work_order_id}", response_model=work_order_schema.WorkOrder, summary="更新工單狀態或備註")
def update_work_order(
    work_order_id: int, 
    work_order: work_order_schema.WorkOrderUpdate, 
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db)
):
    """
    根據工單 `work_order_id` 更新其資訊。
    主要用於變更工單狀態 (例如：'處理中' -> '已完成') 或修改內部備註。
    """
    try:
        db_work_order = crud.update_work_order(db, work_order_id=work_order_id, work_order_update=work_order)
        if db_work_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
        return db_work_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{work_order_id}", response_model=work_order_schema.WorkOrder, summary="刪除工單（軟刪除）")
def delete_work_order(
    work_order_id: int,
    delete: work_order_schema.WorkOrderDeleteCreate,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    if not delete.actor:
        delete.actor = admin["username"] or admin["role"]
    try:
        db_work_order = crud.soft_delete_work_order(db, work_order_id=work_order_id, delete=delete)
        if db_work_order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到該工單")
        return db_work_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
