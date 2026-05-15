from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db import crud, models
from schemas import order as order_schema
from db.database import get_db

router = APIRouter()

@router.get("/user/{google_id}", response_model=List[order_schema.Order], summary="讀取特定使用者的訂單")
def read_user_orders(google_id: str, db: Session = Depends(get_db)):
    orders = db.query(models.Order).filter(models.Order.google_id == google_id).order_by(models.Order.created_at.desc()).all()
    return orders


@router.post("/", response_model=order_schema.Order, summary="建立新訂單")
def create_order(order_data: order_schema.OrderCreate, db: Session = Depends(get_db)):
    """
    消費者下單 API。會自動扣除商品庫存。
    不串金流，訂單建立後狀態為 PENDING，由店家處理後續。
    """
    # 驗證所有商品並計算金額
    total = 0
    order_items = []
    for item in order_data.items:
        product = db.query(models.Product).get(item.product_id)
        if not product:
            raise HTTPException(status_code=400, detail=f"找不到商品 ID={item.product_id}")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"商品 [{product.name}] 已下架")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"商品 [{product.name}] 庫存不足（剩餘 {product.stock}）")

        # 使用當時的商品價格，避免前端價格被竄改
        unit_price = product.price
        total += unit_price * item.quantity

        order_items.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
        })

        # 扣庫存
        product.stock -= item.quantity

    # 建立訂單
    order = models.Order(
        google_id=order_data.google_id,
        total_amount=total,
        recipient_name=order_data.recipient_name,
        recipient_phone=order_data.recipient_phone,
        shipping_address=order_data.shipping_address,
        notes=order_data.notes,
        status=models.OrderStatus.PENDING,
    )
    db.add(order)
    db.flush()

    # 建立訂單項目
    for oi in order_items:
        db.add(models.OrderItem(order_id=order.id, **oi))

    db.commit()
    db.refresh(order)
    return order


# ========== 管理端 API ==========

@router.get("/", response_model=List[order_schema.Order], summary="取得所有訂單")
def get_all_orders(db: Session = Depends(get_db)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()


@router.post("/admin", response_model=order_schema.Order, summary="管理員新增現場訂單")
def create_instore_order(order_data: order_schema.AdminOrderCreate, db: Session = Depends(get_db)):
    """
    管理員為現場客人建立訂單。消費金額會自動加入會員累積消費。
    """
    # 驗證會員是否存在
    user = db.query(models.User).filter(models.User.google_id == order_data.google_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="找不到該會員")

    order = models.Order(
        google_id=order_data.google_id,
        total_amount=order_data.total_amount,
        recipient_name=order_data.recipient_name,
        recipient_phone=order_data.recipient_phone,
        shipping_address="現場取貨",
        notes=order_data.notes,
        status=models.OrderStatus.PENDING,
        source="instore"
    )
    db.add(order)
    db.flush()

    # 處理訂單項目（如果有的話）
    for item in order_data.items:
        product = db.query(models.Product).get(item.product_id)
        if product and product.stock >= item.quantity:
            product.stock -= item.quantity
        db.add(models.OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        ))

    # 移除自動加入累積消費，統一由狀態更新控制

    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=order_schema.Order, summary="更新訂單狀態")
def update_order_status(order_id: int, status: str, db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")

    # 驗證狀態值
    try:
        new_status = models.OrderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"無效的狀態值: {status}")

    old_status = order.status
    order.status = new_status

    # 如果結案 → 將消費金額加入會員累積消費
    if new_status == models.OrderStatus.COMPLETED and old_status != models.OrderStatus.COMPLETED:
        user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
        if user:
            user.cumulative_consumption = (user.cumulative_consumption or 0) + order.total_amount
    
    # 如果從結案變為其他狀態 (例如反悔或取消) → 扣除累積消費
    elif old_status == models.OrderStatus.COMPLETED and new_status != models.OrderStatus.COMPLETED:
        user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
        if user:
            user.cumulative_consumption = max(0, (user.cumulative_consumption or 0) - order.total_amount)

    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=order_schema.Order, summary="修改現場訂單")
def update_instore_order(order_id: int, update_data: order_schema.OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")
    if order.source != "instore":
        raise HTTPException(status_code=403, detail="線上訂單無法修改，僅限修改現場訂單")

    if update_data.total_amount is not None:
        order.total_amount = update_data.total_amount
    if update_data.recipient_name is not None:
        order.recipient_name = update_data.recipient_name
    if update_data.recipient_phone is not None:
        order.recipient_phone = update_data.recipient_phone
    if update_data.notes is not None:
        order.notes = update_data.notes
    if update_data.status is not None:
        try:
            new_status = models.OrderStatus(update_data.status)
            old_status = order.status
            
            if new_status != old_status:
                order.status = new_status
                # 處理累積消費邏輯
                if new_status == models.OrderStatus.COMPLETED:
                    user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
                    if user:
                        user.cumulative_consumption = (user.cumulative_consumption or 0) + order.total_amount
                elif old_status == models.OrderStatus.COMPLETED:
                    user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
                    if user:
                        user.cumulative_consumption = max(0, (user.cumulative_consumption or 0) - order.total_amount)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的狀態值")

    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/cancel", response_model=order_schema.Order, summary="取消訂單")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")
    old_status = order.status
    order.status = models.OrderStatus.CANCELED

    # 如果從結案變更為取消 → 扣除累積消費
    if old_status == models.OrderStatus.COMPLETED:
        user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
        if user:
            user.cumulative_consumption = max(0, (user.cumulative_consumption or 0) - order.total_amount)

    # 恢復庫存
    for item in order.items:
        product = db.query(models.Product).get(item.product_id)
        if product:
            product.stock += item.quantity

    db.commit()
    db.refresh(order)
    return order
