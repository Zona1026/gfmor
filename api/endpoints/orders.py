from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from db import accounting as accounting_service
from db import crud, inventory as inventory_service, models
from db.points import sync_order_points
from schemas import order as order_schema
from schemas import accounting as accounting_schema
from api.dependencies.admin_auth import (
    auth_context,
    ensure_self_or_manager,
    require_manager_admin,
    require_self_or_admin,
)
from db.database import get_db

router = APIRouter()


def _consume_online_order_inventory(db: Session, order):
    if order.source != "online":
        return
    for item in order.items:
        inventory_service.consume_order_item(db, item)


def _restore_or_release_order_inventory(db: Session, order, was_completed: bool):
    for item in order.items:
        product = item.product or db.query(models.Product).get(item.product_id)
        if not product:
            continue

        if order.source == "online":
            if was_completed:
                inventory_service.restore_inventory(
                    db,
                    product,
                    item.quantity,
                    inventory_service.SOURCE_ORDER_ITEM,
                    item.id,
                    reason=f"Order #{order.id} canceled",
                )
            elif inventory_service.has_order_item_reservation(db, item):
                inventory_service.release_order_item(db, item)
            else:
                inventory_service.restore_inventory(
                    db,
                    product,
                    item.quantity,
                    inventory_service.SOURCE_ORDER_ITEM,
                    item.id,
                    reason=f"Legacy order #{order.id} canceled",
                )
        elif order.source == "instore":
            inventory_service.restore_inventory(
                db,
                product,
                item.quantity,
                inventory_service.SOURCE_ORDER_ITEM,
                item.id,
                reason=f"In-store order #{order.id} canceled",
            )


def _order_item_query(db: Session):
    return (
        db.query(models.OrderItem)
        .options(
            joinedload(models.OrderItem.product),
            joinedload(models.OrderItem.order),
            joinedload(models.OrderItem.notifications),
        )
    )

@router.get("/user/{google_id}", response_model=List[order_schema.Order], summary="讀取特定使用者的訂單")
def read_user_orders(
    google_id: str,
    auth=Depends(require_self_or_admin),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.items).joinedload(models.OrderItem.product))
        .options(joinedload(models.Order.items).joinedload(models.OrderItem.notifications))
        .filter(models.Order.google_id == google_id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return orders


@router.post("/", response_model=order_schema.Order, summary="建立新訂單")
def create_order(
    order_data: order_schema.OrderCreate,
    auth=Depends(auth_context),
    db: Session = Depends(get_db),
):
    """
    消費者下單 API。會自動扣除商品庫存。
    不串金流，訂單建立後狀態為 PENDING，由店家處理後續。
    """
    if not order_data.google_id:
        raise HTTPException(status_code=400, detail="線上訂單需要會員 google_id")
    ensure_self_or_manager(order_data.google_id, auth)

    user = db.query(models.User).filter(models.User.google_id == order_data.google_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="找不到該會員")

    # 驗證所有商品並計算金額
    total = 0
    order_items = []
    for item in order_data.items:
        product = db.query(models.Product).get(item.product_id)
        if not product:
            raise HTTPException(status_code=400, detail=f"找不到商品 ID={item.product_id}")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"商品 [{product.name}] 已下架")
        if inventory_service.available_stock(db, product) < item.quantity:
            raise HTTPException(status_code=400, detail=f"商品 [{product.name}] 可用庫存不足（可用 {inventory_service.available_stock(db, product)}）")

        # 使用當時的商品價格，避免前端價格被竄改
        unit_price = product.price
        total += unit_price * item.quantity

        order_items.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "product": product,
        })

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
        product = oi.pop("product")
        order_item = models.OrderItem(order_id=order.id, product=product, **oi)
        db.add(order_item)
        db.flush()
        inventory_service.reserve_order_item(db, order_item)

    db.commit()
    db.refresh(order)
    return order


# ========== 管理端 API ==========

def _orders_query(db: Session):
    return (
        db.query(models.Order)
        .options(
            joinedload(models.Order.guest_customer),
            joinedload(models.Order.items).joinedload(models.OrderItem.product),
            joinedload(models.Order.items).joinedload(models.OrderItem.notifications),
        )
    )


@router.get("/", response_model=List[order_schema.Order], summary="取得所有訂單")
def get_all_orders(
    source: Optional[str] = None,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    query = _orders_query(db)
    if source:
        if source not in ["online", "instore"]:
            raise HTTPException(status_code=400, detail="source 僅支援 online 或 instore")
        query = query.filter(models.Order.source == source)
    return (
        query
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.get("/shop", response_model=List[order_schema.Order], summary="取得商城網站訂單")
def get_shop_orders(admin=Depends(require_manager_admin), db: Session = Depends(get_db)):
    return (
        _orders_query(db)
        .filter(models.Order.source == "online")
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.post("/admin", response_model=order_schema.Order, summary="管理員新增現場訂單")
def create_instore_order(
    order_data: order_schema.AdminOrderCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    """
    管理員為現場客人建立訂單。會員訂單會綁定 google_id；
    散客訂單會綁定 guest_customer_id，直到手動合併前不計入會員累積消費。
    """
    google_id = None
    guest_customer_id = None
    recipient_name = order_data.recipient_name
    recipient_phone = order_data.recipient_phone

    if order_data.customer_type == "member":
        # 驗證會員是否存在
        user = db.query(models.User).filter(models.User.google_id == order_data.google_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="找不到該會員")
        google_id = user.google_id
        recipient_name = recipient_name or user.name
        recipient_phone = recipient_phone or user.phone or ""
    elif order_data.customer_type == "guest":
        if order_data.guest_customer_id:
            guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == order_data.guest_customer_id).first()
            if not guest:
                raise HTTPException(status_code=400, detail="找不到該散客")
        else:
            guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.phone == order_data.guest_phone).first()
            if guest:
                guest.name = order_data.guest_name or guest.name
                if order_data.guest_notes is not None:
                    guest.notes = order_data.guest_notes
            else:
                guest = models.GuestCustomer(
                    name=order_data.guest_name,
                    phone=order_data.guest_phone,
                    notes=order_data.guest_notes,
                )
                db.add(guest)
                db.flush()

        guest_customer_id = guest.id
        recipient_name = order_data.guest_name or guest.name
        recipient_phone = order_data.guest_phone or guest.phone
    else:
        raise HTTPException(status_code=400, detail="customer_type 必須是 member 或 guest")

    order = models.Order(
        google_id=google_id,
        guest_customer_id=guest_customer_id,
        total_amount=order_data.total_amount,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
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
        if not product:
            raise HTTPException(status_code=400, detail=f"商品 ID={item.product_id} 不存在")
        order_item = models.OrderItem(
            order_id=order.id,
            product=product,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        db.add(order_item)
        db.flush()
        try:
            inventory_service.deduct_immediate(
                db,
                product,
                item.quantity,
                models.InventoryMovementType.INSTORE_SALE,
                inventory_service.SOURCE_ORDER_ITEM,
                order_item.id,
                reason=f"In-store order #{order.id}",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # 移除自動加入累積消費，統一由狀態更新控制

    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/payment-status", response_model=order_schema.Order, summary="更新商城訂單付款狀態")
def update_order_payment_status(
    order_id: int,
    update: accounting_schema.OrderPaymentStatusUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到訂單")
    if order.source != "online":
        raise HTTPException(status_code=400, detail="只有商城訂單可以更新商城付款狀態")

    try:
        accounting_service.update_shop_order_payment_status(db, order, update)
        db.commit()
        db.refresh(order)
        return order
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/{order_id}/status", response_model=order_schema.Order, summary="更新訂單狀態")
def update_order_status(
    order_id: int,
    status: str,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
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
    if new_status == models.OrderStatus.COMPLETED:
        for item in order.items:
            item.status = models.OrderItemStatus.COMPLETED
        if old_status != models.OrderStatus.COMPLETED:
            try:
                _consume_online_order_inventory(db, order)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
    elif new_status == models.OrderStatus.CANCELED and old_status != models.OrderStatus.CANCELED:
        order.payment_status = models.OrderPaymentStatus.CANCELED
        _restore_or_release_order_inventory(db, order, old_status == models.OrderStatus.COMPLETED)

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

    sync_order_points(db, order)

    db.commit()
    db.refresh(order)
    return order


@router.put("/{order_id}", response_model=order_schema.Order, summary="修改現場訂單")
def update_instore_order(
    order_id: int,
    update_data: order_schema.OrderUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")
    if order.source != "instore":
        raise HTTPException(status_code=403, detail="線上訂單無法修改，僅限修改現場訂單")

    old_status = order.status
    old_total_amount = order.total_amount or 0

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
            if new_status != old_status:
                order.status = new_status
                if new_status == models.OrderStatus.COMPLETED:
                    for item in order.items:
                        item.status = models.OrderItemStatus.COMPLETED
                elif new_status == models.OrderStatus.CANCELED:
                    order.payment_status = models.OrderPaymentStatus.CANCELED
                    _restore_or_release_order_inventory(db, order, old_status == models.OrderStatus.COMPLETED)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"無效的狀態值")

    old_completed_amount = old_total_amount if old_status == models.OrderStatus.COMPLETED else 0
    new_completed_amount = order.total_amount if order.status == models.OrderStatus.COMPLETED else 0
    consumption_delta = new_completed_amount - old_completed_amount

    if consumption_delta != 0:
        user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
        if user:
            user.cumulative_consumption = max(0, (user.cumulative_consumption or 0) + consumption_delta)

    sync_order_points(db, order)

    db.commit()
    db.refresh(order)
    return order


@router.post(
    "/items/{item_id}/notifications",
    response_model=order_schema.OrderItem,
    status_code=status.HTTP_201_CREATED,
    summary="記錄訂單商品到貨通知",
)
def create_order_item_notification(
    item_id: int,
    notification: order_schema.OrderItemNotificationCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    item = _order_item_query(db).filter(models.OrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="找不到該訂單商品")
    if item.order and item.order.status == models.OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="已結案訂單的商品不可記錄通知")
    if item.status != models.OrderItemStatus.ARRIVED_NEED_NOTIFY:
        raise HTTPException(status_code=400, detail="只有已到貨需通知的商品可以記錄通知")

    method = notification.method.strip()
    if not method:
        raise HTTPException(status_code=400, detail="通知方式為必填")

    order = item.order
    record = models.OrderItemNotification(
        order_item_id=item.id,
        order_id=item.order_id,
        method=method,
        recipient_name=order.recipient_name if order else None,
        recipient_phone=order.recipient_phone if order else None,
        note=notification.note,
        actor=admin["username"] or admin["role"],
        notified_at=notification.notified_at or datetime.utcnow(),
    )
    db.add(record)
    item.status = models.OrderItemStatus.NOTIFIED
    db.commit()

    return _order_item_query(db).filter(models.OrderItem.id == item_id).first()


@router.patch("/items/{item_id}/status", response_model=order_schema.OrderItem, summary="更新訂單商品狀態")
def update_order_item_status(
    item_id: int,
    update_data: order_schema.OrderItemStatusUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    item = _order_item_query(db).filter(models.OrderItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="找不到該訂單商品")
    if item.order and item.order.status == models.OrderStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="已結案訂單的商品狀態不可手動修改")
    if update_data.status == models.OrderItemStatus.NOTIFIED:
        raise HTTPException(status_code=400, detail="請使用到貨通知紀錄功能標記已通知")

    item.status = update_data.status
    db.commit()
    return _order_item_query(db).filter(models.OrderItem.id == item_id).first()


@router.patch("/{order_id}/cancel", response_model=order_schema.Order, summary="取消訂單")
def cancel_order(
    order_id: int,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")
    old_status = order.status
    if old_status == models.OrderStatus.CANCELED:
        return order
    order.status = models.OrderStatus.CANCELED
    order.payment_status = models.OrderPaymentStatus.CANCELED

    # 如果從結案變更為取消 → 扣除累積消費
    if old_status == models.OrderStatus.COMPLETED:
        user = db.query(models.User).filter(models.User.google_id == order.google_id).first()
        if user:
            user.cumulative_consumption = max(0, (user.cumulative_consumption or 0) - order.total_amount)

    # 恢復庫存
    _restore_or_release_order_inventory(db, order, old_status == models.OrderStatus.COMPLETED)

    sync_order_points(db, order)

    db.commit()
    db.refresh(order)
    return order
