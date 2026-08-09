from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

# 引入我們建立的 models 和 schemas
from . import inventory as inventory_service
from . import models
from . import accounting as accounting_service
from . import purchases as purchase_service
from schemas.user import UserCreate, UserUpdate
from schemas.product import ProductCreate, ProductUpdate

# =================================================================
# User CRUD (使用者相關)
# =================================================================

def get_user(db: Session, google_id: str):
    """
    根據 Google ID 獲取單一使用者。
    """
    return db.query(models.User).filter(models.User.google_id == google_id).first()

def get_user_by_email(db: Session, email: str):
    """
    根據 Email 獲取單一使用者。
    """
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """
    獲取使用者列表，支援分頁。
    """
    return db.query(models.User).offset(skip).limit(limit).all()

def get_users_by_name(db: Session, name: str, skip: int = 0, limit: int = 10):
    """
    根據姓名模糊搜尋使用者。
    """
    if not name:
        return []
    search_pattern = f"%{name}%"
    # 使用 ilike 進行不區分大小寫的模糊搜尋
    return db.query(models.User).filter(models.User.name.ilike(search_pattern)).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    """
    建立新使用者，並可選擇性地同時建立其車籍資料。
    """
    # 先將車籍資料從 user DTO 中分離出來
    motors_data = user.motors
    # 使用 exclude 參數來建立一個不含 'motors' 的字典
    user_data = user.dict(exclude={'motors'})

    # 根據過濾後的資料建立 User 物件
    db_user = models.User(**user_data)
    db.add(db_user)
    
    # 先提交一次，這樣 db_user 才能獲得由資料庫產生的 id
    # 並且讓後續的關聯操作可以找到這位使用者
    db.commit()
    db.refresh(db_user)

    # 如果有提供車籍資料，則逐一建立
    if motors_data:
        for motor_data in motors_data:
            db_motor = models.Motor(
                **motor_data.dict(),
                google_id=db_user.google_id  # 確保車輛關聯到這位新使用者
            )
            db.add(db_motor)
        
        # 再次提交，以儲存新建立的車籍資料
        db.commit()
        # 刷新使用者物件以載入剛建立的關聯車輛
        db.refresh(db_user)

    return db_user

def update_user(db: Session, google_id: str, user_update: UserUpdate):
    """
    根據 Google ID 更新使用者資訊，並可選擇性地為其新增車籍資料。
    """
    db_user = get_user(db, google_id=google_id)
    if not db_user:
        return None
    
    # 分離出車籍資料和使用者基本資料
    motors_data = user_update.motors
    update_data = user_update.dict(exclude_unset=True, exclude={'motors'})

    # 1. 更新使用者基本欄位
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)

    # 2. 如果有提供新的車籍資料，則逐一建立
    if motors_data:
        for motor_data in motors_data:
            # 檢查該車牌是否已存在
            existing_motor = db.query(models.Motor).filter(models.Motor.license_plate == motor_data.license_plate).first()
            if existing_motor:
                # 如果車牌已存在且屬於同一位使用者，我們就跳過新增 (或者在此更新)
                if existing_motor.google_id == db_user.google_id:
                    continue
                else:
                    raise ValueError(f"車牌 '{motor_data.license_plate}' 已經被其他使用者註冊了！")
            
            new_motor = models.Motor(
                **motor_data.dict(),
                google_id=db_user.google_id  # 確保新車輛關聯到這位使用者
            )
            db.add(new_motor)
            
    # 3. 提交所有變更 (包含使用者更新和新增的車輛)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
        
    # 刷新使用者物件，以載入所有關聯資料 (包括剛才新增的車輛)
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, google_id: str):
    """
    根據 Google ID 刪除使用者 (安全刪除)。
    如果使用者底下還有車籍、預約、或訂單紀錄，將不允許刪除。
    """
    db_user = get_user(db, google_id=google_id)
    if not db_user:
        # 如果使用者不存在，也算是一種「成功刪除」的情境，回傳 True
        return True
    
    # 檢查關聯紀錄
    if db_user.motors or db_user.bookings or db_user.orders:
        raise ValueError(f"無法刪除使用者 '{db_user.name}' (ID: {google_id})，因為該使用者尚有關聯的車籍、預約或訂單紀錄。")

    db.delete(db_user)
    db.commit()
    return True


# =================================================================
# Product CRUD (商品相關)
# =================================================================

def get_product(db: Session, product_id: int):
    """
    根據 ID 獲取單一商品。
    """
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    """
    獲取商品列表，支援分頁。
    """
    return db.query(models.Product).order_by(models.Product.id).offset(skip).limit(limit).all()

def create_product(db: Session, product: ProductCreate):
    """
    建立新商品。
    """
    # 使用 **product.dict() 可以快速地將 Pydantic 模型解包成關鍵字參數
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product_update: ProductUpdate):
    """
    根據 ID 更新商品資訊。
    """
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    
    # exclude_unset=True 表示只取有被前端明確給定的值
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
        
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    """
    根據 ID 刪除商品。
    """
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

# =================================================================
# WorkOrder CRUD (工單相關)
# =================================================================

from schemas.work_order import (
    WorkOrderApprovalReview,
    WorkOrderCreate,
    WorkOrderDeleteCreate,
    WorkOrderLineItemCreate,
    WorkOrderPaymentCreate,
    WorkOrderUpdate,
)
from datetime import datetime, timedelta

HIGH_QUOTE_APPROVAL_THRESHOLD = 30000
APPROVAL_GATED_STATUSES = [
    models.WorkOrderStatus.IN_PROGRESS,
    models.WorkOrderStatus.AWAITING_PAYMENT,
    models.WorkOrderStatus.COMPLETED,
]


def _work_order_options():
    return (
        joinedload(models.WorkOrder.booking).joinedload(models.Booking.user),
        joinedload(models.WorkOrder.booking).joinedload(models.Booking.motor),
        joinedload(models.WorkOrder.user),
        joinedload(models.WorkOrder.guest_customer),
        joinedload(models.WorkOrder.guest_motor),
        joinedload(models.WorkOrder.motor),
        joinedload(models.WorkOrder.items).joinedload(models.WorkOrderItem.product),
        joinedload(models.WorkOrder.line_items).joinedload(models.WorkOrderLineItem.product),
        joinedload(models.WorkOrder.line_items).joinedload(models.WorkOrderLineItem.purchase_requests),
        joinedload(models.WorkOrder.line_items).joinedload(models.WorkOrderLineItem.purchase_requests).joinedload(models.PurchaseRequest.product),
        joinedload(models.WorkOrder.payments),
        joinedload(models.WorkOrder.approvals),
    )


def _schema_dict(schema, **kwargs):
    if hasattr(schema, "model_dump"):
        return schema.model_dump(**kwargs)
    return schema.dict(**kwargs)


def _booking_service_type(category):
    if category == models.BookingCategory.REPAIR:
        return models.WorkOrderServiceType.REPAIR
    if category == models.BookingCategory.MAINTENANCE:
        return models.WorkOrderServiceType.MAINTENANCE
    return models.WorkOrderServiceType.REPAIR


def _line_total(line_item):
    return max(0, line_item.quantity or 0) * max(0, line_item.unit_price or 0)


def _recalculate_work_order_total(db_work_order):
    subtotal = 0
    discount = 0
    for line_item in db_work_order.line_items:
        amount = _line_total(line_item)
        if line_item.type == models.WorkOrderLineItemType.DISCOUNT:
            discount += amount
        else:
            subtotal += amount
    db_work_order.total_amount = max(0, subtotal - discount)
    return db_work_order.total_amount


def _sync_payment_status(db_work_order):
    if db_work_order.payment_status == models.WorkOrderPaymentStatus.REFUNDED:
        return
    paid_amount = db_work_order.paid_amount
    total_amount = db_work_order.total_amount or 0
    if paid_amount <= 0:
        db_work_order.payment_status = models.WorkOrderPaymentStatus.UNPAID
    elif paid_amount < total_amount:
        db_work_order.payment_status = models.WorkOrderPaymentStatus.PARTIALLY_PAID
    else:
        db_work_order.payment_status = models.WorkOrderPaymentStatus.PAID


def _ensure_work_order_approval(db_work_order, approval_type, title, reason, active_statuses=None):
    if active_statuses is None:
        active_statuses = [
            models.WorkOrderApprovalStatus.PENDING,
            models.WorkOrderApprovalStatus.APPROVED,
        ]
    existing = [
        approval for approval in db_work_order.approvals
        if approval.type == approval_type and approval.status in active_statuses
    ]
    if existing:
        return existing[0]
    approval = models.WorkOrderApproval(
        type=approval_type,
        title=title,
        reason=reason,
    )
    db_work_order.approvals.append(approval)
    return approval


def _open_purchase_request_quantity(line_item):
    quantity = 0
    for request in line_item.purchase_requests or []:
        if request.status == models.PurchaseRequestStatus.CANCELED:
            continue
        quantity += max(0, (request.requested_quantity or 0) - (request.assigned_quantity or 0))
    return quantity


def _needs_inventory_reservation_approval(db_work_order):
    for line_item in db_work_order.line_items:
        if line_item.type != models.WorkOrderLineItemType.PART:
            continue
        if not line_item.product_id or not line_item.is_confirmed or line_item.inventory_deducted:
            continue
        remaining = max(0, (line_item.quantity or 0) - (line_item.inventory_consumed_quantity or 0))
        covered = (line_item.inventory_reserved_quantity or 0) + _open_purchase_request_quantity(line_item)
        if remaining > covered:
            return True
    return False


def _has_reserved_unconsumed_inventory(db_work_order):
    return any(
        line_item.type == models.WorkOrderLineItemType.PART
        and line_item.product_id
        and (line_item.inventory_reserved_quantity or 0) > 0
        for line_item in db_work_order.line_items
    )


def _inventory_fully_consumed(db_work_order):
    part_items = [
        line_item for line_item in db_work_order.line_items
        if line_item.type == models.WorkOrderLineItemType.PART
        and line_item.product_id
        and line_item.is_confirmed
    ]
    if not part_items:
        return True
    return all(
        (line_item.inventory_consumed_quantity or 0) >= (line_item.quantity or 0)
        for line_item in part_items
    )


def _request_inventory_reservation_approval(db_work_order):
    if not _needs_inventory_reservation_approval(db_work_order):
        return None
    db_work_order.status = models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING
    return _ensure_work_order_approval(
        db_work_order,
        models.WorkOrderApprovalType.INVENTORY_RESERVATION,
        "確認預留庫存",
        "工單零件 / 耗材需主管確認後才可預留或產生叫貨需求。",
        active_statuses=[models.WorkOrderApprovalStatus.PENDING],
    )


def _request_inventory_consumption_approval(db_work_order):
    if not _has_reserved_unconsumed_inventory(db_work_order):
        return None
    return _ensure_work_order_approval(
        db_work_order,
        models.WorkOrderApprovalType.INVENTORY_CONSUMPTION,
        "確認扣庫存",
        "工單完工前需主管確認扣除已預留零件 / 耗材。",
        active_statuses=[models.WorkOrderApprovalStatus.PENDING],
    )


def _sync_work_order_approvals(db_work_order):
    discount_total = sum(
        _line_total(item)
        for item in db_work_order.line_items
        if item.type == models.WorkOrderLineItemType.DISCOUNT
    )
    if discount_total > 0:
        _ensure_work_order_approval(
            db_work_order,
            models.WorkOrderApprovalType.DISCOUNT,
            "工單折扣需主管確認",
            f"工單 #{db_work_order.id or '新工單'} 含折扣 NT$ {discount_total}",
        )
    if (db_work_order.total_amount or 0) >= HIGH_QUOTE_APPROVAL_THRESHOLD:
        _ensure_work_order_approval(
            db_work_order,
            models.WorkOrderApprovalType.HIGH_QUOTE,
            "高額報價需主管確認",
            f"工單金額 NT$ {db_work_order.total_amount}",
        )
    if db_work_order.status == models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING and not any(
        approval.type == models.WorkOrderApprovalType.INVENTORY_RESERVATION
        for approval in db_work_order.approvals
    ):
        _ensure_work_order_approval(
            db_work_order,
            models.WorkOrderApprovalType.STATUS_CHANGE,
            "工單狀態需主管確認",
            "此工單已送主管確認。",
        )

    _request_inventory_reservation_approval(db_work_order)


def _has_blocking_approval(db_work_order, target_status=None):
    pending = [
        approval for approval in db_work_order.approvals
        if approval.status == models.WorkOrderApprovalStatus.PENDING
    ]
    if target_status == models.WorkOrderStatus.AWAITING_PAYMENT:
        return any(
            approval.type != models.WorkOrderApprovalType.INVENTORY_CONSUMPTION
            for approval in pending
        )
    return bool(pending)


def _build_line_item(db: Session, item_in: WorkOrderLineItemCreate):
    item_data = _schema_dict(item_in)
    item_type = item_data["type"]
    if item_data.get("quantity", 0) <= 0:
        raise ValueError("工單明細數量需大於 0")
    if item_data.get("unit_price", 0) < 0:
        raise ValueError("工單明細單價不可小於 0")

    db_product = None
    if item_data.get("product_id"):
        db_product = get_product(db, product_id=item_data["product_id"])
        if not db_product:
            raise ValueError(f"找不到ID為 {item_data['product_id']} 的商品")
        if item_type == models.WorkOrderLineItemType.PART and not item_data.get("unit_price"):
            item_data["unit_price"] = db_product.price
        if not item_data.get("name"):
            item_data["name"] = db_product.name

    if item_type == models.WorkOrderLineItemType.PART and not item_data.get("product_id"):
        raise ValueError("零件 / 耗材明細必須選擇商品")
    if not item_data.get("name"):
        raise ValueError("工單明細名稱為必填")

    db_item = models.WorkOrderLineItem(**item_data)
    if db_product:
        db_item.product = db_product
    return db_item


def _legacy_items_to_line_items(db: Session, legacy_items):
    line_items = []
    for item_in in legacy_items:
        db_product = get_product(db, product_id=item_in.product_id)
        if not db_product:
            raise ValueError(f"找不到ID為 {item_in.product_id} 的商品")
        line_items.append(models.WorkOrderLineItem(
            type=models.WorkOrderLineItemType.PART,
            name=db_product.name,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            unit_price=db_product.price,
            is_confirmed=1,
            product=db_product,
        ))
    return line_items


def _work_order_inventory_line_items(db_work_order):
    for line_item in db_work_order.line_items:
        if line_item.type != models.WorkOrderLineItemType.PART:
            continue
        if not line_item.product_id or not line_item.is_confirmed or line_item.inventory_deducted:
            continue
        if not line_item.product:
            raise ValueError(f"Work order line '{line_item.name}' has no product.")
        yield line_item


def _reserve_work_order_inventory(db: Session, db_work_order, actor: str = None):
    db.flush()
    for line_item in _work_order_inventory_line_items(db_work_order):
        purchase_service.sync_line_item_supply(db, line_item, actor=actor)


def _release_work_order_inventory(db: Session, db_work_order):
    for line_item in db_work_order.line_items:
        if line_item.type == models.WorkOrderLineItemType.PART and line_item.product_id and not line_item.inventory_deducted:
            inventory_service.release_work_order_line_item(db, line_item)


def _detach_line_item_purchase_requests(db: Session, line_item):
    requests = (
        db.query(models.PurchaseRequest)
        .filter(
            models.PurchaseRequest.work_order_line_item_id == line_item.id,
            models.PurchaseRequest.status != models.PurchaseRequestStatus.CANCELED,
        )
        .all()
    )
    for request in requests:
        if request.assigned_quantity and not (line_item.inventory_consumed_quantity or 0):
            request.assigned_quantity = max(
                0,
                (request.assigned_quantity or 0) - (line_item.inventory_reserved_quantity or 0),
            )
        request.work_order_line_item_id = None
        if request.unassigned_arrived_quantity > 0:
            request.status = models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT
        elif request.assigned_quantity:
            request.status = models.PurchaseRequestStatus.PARTIAL_ARRIVED
        else:
            request.status = models.PurchaseRequestStatus.CANCELED


def _detach_work_order_purchase_requests(db: Session, db_work_order):
    for line_item in db_work_order.line_items:
        _detach_line_item_purchase_requests(db, line_item)


def _consume_work_order_inventory(db: Session, db_work_order, actor: str = None):
    db.flush()
    for line_item in _work_order_inventory_line_items(db_work_order):
        if (line_item.inventory_reserved_quantity or 0) > 0:
            inventory_service.consume_work_order_line_item(db, line_item, actor=actor)


def _hydrate_from_booking(db_work_order, db_booking):
    db_work_order.google_id = db_booking.google_id
    db_work_order.motor_id = db_booking.motor_id
    db_work_order.customer_name = db_booking.user.name if db_booking.user else None
    db_work_order.customer_phone = db_booking.user.phone if db_booking.user else None
    if db_booking.motor:
        db_work_order.vehicle_license_plate = db_booking.motor.license_plate
        db_work_order.vehicle_brand = db_booking.motor.brand
        db_work_order.vehicle_model = db_booking.motor.model_name
        db_work_order.vehicle_vin = db_booking.motor.vin
        db_work_order.vehicle_mileage = db_booking.motor.mileage
    db_work_order.service_type = _booking_service_type(db_booking.category)
    db_work_order.scheduled_at = db_booking.booking_time
    if db_work_order.notes is None:
        db_work_order.notes = db_booking.notes


def _upsert_guest_motor_for_work_order(db: Session, guest_id: int, work_order: WorkOrderCreate, db_work_order):
    license_plate = work_order.vehicle_license_plate or db_work_order.vehicle_license_plate
    if not license_plate:
        return None

    guest_motor = (
        db.query(models.GuestMotor)
        .filter(
            models.GuestMotor.guest_customer_id == guest_id,
            models.GuestMotor.license_plate == license_plate,
            models.GuestMotor.status.is_(None),
        )
        .first()
    )
    if not guest_motor:
        guest_motor = models.GuestMotor(
            guest_customer_id=guest_id,
            license_plate=license_plate,
        )
        db.add(guest_motor)
        db.flush()

    if work_order.vehicle_brand is not None:
        guest_motor.brand = work_order.vehicle_brand
    if work_order.vehicle_model is not None:
        guest_motor.model_name = work_order.vehicle_model
    if work_order.vehicle_vin is not None:
        guest_motor.vin = work_order.vehicle_vin
    if work_order.vehicle_mileage is not None:
        guest_motor.mileage = work_order.vehicle_mileage

    db_work_order.guest_motor_id = guest_motor.id
    return guest_motor


def _hydrate_direct_customer(db: Session, db_work_order, work_order: WorkOrderCreate):
    if work_order.google_id and (work_order.guest_customer_id or work_order.guest_name or work_order.guest_phone):
        raise ValueError("工單不可同時綁定會員與散客")

    if work_order.google_id:
        db_user = get_user(db, google_id=work_order.google_id)
        if not db_user:
            raise ValueError(f"找不到會員 Google ID={work_order.google_id}")
        db_work_order.google_id = db_user.google_id
        db_work_order.customer_name = work_order.customer_name or db_user.name
        db_work_order.customer_phone = work_order.customer_phone or db_user.phone

        if work_order.motor_id:
            db_motor = get_motor(db, motor_id=work_order.motor_id)
            if not db_motor:
                raise ValueError(f"找不到車輛 ID={work_order.motor_id}")
            if db_motor.google_id != db_user.google_id:
                raise ValueError("車輛不屬於此會員")
            db_work_order.motor_id = db_motor.id
            db_work_order.vehicle_license_plate = work_order.vehicle_license_plate or db_motor.license_plate
            db_work_order.vehicle_brand = work_order.vehicle_brand or db_motor.brand
            db_work_order.vehicle_model = work_order.vehicle_model or db_motor.model_name
            db_work_order.vehicle_vin = work_order.vehicle_vin or db_motor.vin
            db_work_order.vehicle_mileage = work_order.vehicle_mileage if work_order.vehicle_mileage is not None else db_motor.mileage
    else:
        guest = None
        if work_order.guest_customer_id:
            guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == work_order.guest_customer_id).first()
            if not guest:
                raise ValueError(f"找不到散客 ID={work_order.guest_customer_id}")
        elif work_order.guest_name and work_order.guest_phone:
            guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.phone == work_order.guest_phone).first()
            if guest:
                guest.name = work_order.guest_name
            else:
                guest = models.GuestCustomer(name=work_order.guest_name, phone=work_order.guest_phone)
                db.add(guest)
                db.flush()
        else:
            raise ValueError("現場工單需提供會員或散客資料")

        db_work_order.guest_customer_id = guest.id
        db_work_order.customer_name = work_order.customer_name or guest.name
        db_work_order.customer_phone = work_order.customer_phone or guest.phone

        if work_order.guest_motor_id:
            guest_motor = get_guest_motor(db, guest_motor_id=work_order.guest_motor_id)
            if not guest_motor:
                raise ValueError(f"找不到散客車輛 ID={work_order.guest_motor_id}")
            if guest_motor.guest_customer_id != guest.id:
                raise ValueError("散客車輛不屬於此散客")
            db_work_order.guest_motor_id = guest_motor.id
            db_work_order.vehicle_license_plate = work_order.vehicle_license_plate or guest_motor.license_plate
            db_work_order.vehicle_brand = work_order.vehicle_brand or guest_motor.brand
            db_work_order.vehicle_model = work_order.vehicle_model or guest_motor.model_name
            db_work_order.vehicle_vin = work_order.vehicle_vin or guest_motor.vin
            db_work_order.vehicle_mileage = work_order.vehicle_mileage if work_order.vehicle_mileage is not None else guest_motor.mileage

    if work_order.vehicle_license_plate:
        db_work_order.vehicle_license_plate = work_order.vehicle_license_plate
    db_work_order.vehicle_brand = work_order.vehicle_brand or db_work_order.vehicle_brand
    db_work_order.vehicle_model = work_order.vehicle_model or db_work_order.vehicle_model
    db_work_order.vehicle_vin = work_order.vehicle_vin or db_work_order.vehicle_vin
    if work_order.vehicle_mileage is not None:
        db_work_order.vehicle_mileage = work_order.vehicle_mileage

    if db_work_order.guest_customer_id:
        _upsert_guest_motor_for_work_order(db, db_work_order.guest_customer_id, work_order, db_work_order)

    if not db_work_order.customer_name or not db_work_order.customer_phone:
        raise ValueError("工單需有客戶姓名與電話")
    if not db_work_order.vehicle_license_plate:
        raise ValueError("工單需有車牌或設備識別資料")
    if not str(db_work_order.vehicle_model or "").strip():
        raise ValueError("工單需有車型或設備資料")
    if db_work_order.vehicle_mileage is None:
        raise ValueError("工單需有里程資料")
    if not str(db_work_order.responsible_staff or "").strip():
        raise ValueError("工單需有負責人")

def get_work_order(db: Session, work_order_id: int):
    """
    根據 ID 獲取單一工單及其所有項目。
    """
    # SQLAlchemy 會自動處理 relationship，當我們查詢 WorkOrder 時，
    # 它關聯的 items 也會被載入 (因為 Pydantic schema 有宣告)。
    return (
        db.query(models.WorkOrder)
        .options(*_work_order_options())
        .filter(models.WorkOrder.id == work_order_id)
        .first()
    )

def get_work_orders(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    status: str = None,
    date_str: str = None,
    q: str = None,
    service_type: str = None,
    payment_status: str = None,
    responsible_staff: str = None,
    include_deleted: bool = False,
):
    """
    獲取工單列表，支援分頁、狀態、日期與關鍵字搜尋。
    """
    query = (
        db.query(models.WorkOrder)
        .options(*_work_order_options())
        .outerjoin(models.WorkOrder.booking)
        .outerjoin(models.Booking.user)
        .outerjoin(models.Booking.motor)
    )
    if not include_deleted:
        query = query.filter(models.WorkOrder.deleted_at.is_(None))

    if status:
        if status == "active":
            query = query.filter(models.WorkOrder.status.in_([
                models.WorkOrderStatus.PENDING,
                models.WorkOrderStatus.INSPECTION_PENDING,
                models.WorkOrderStatus.QUOTE_PENDING,
                models.WorkOrderStatus.CUSTOMER_CONFIRMATION_PENDING,
                models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING,
                models.WorkOrderStatus.IN_PROGRESS,
            ]))
        elif status == "payment":
            query = query.filter(
                models.WorkOrder.status == models.WorkOrderStatus.AWAITING_PAYMENT,
                models.WorkOrder.payment_status.in_([
                    models.WorkOrderPaymentStatus.UNPAID,
                    models.WorkOrderPaymentStatus.PARTIALLY_PAID,
                ])
            )
        else:
            query = query.filter(models.WorkOrder.status == models.WorkOrderStatus(status))
    if service_type:
        query = query.filter(models.WorkOrder.service_type == models.WorkOrderServiceType(service_type))
    if payment_status:
        query = query.filter(models.WorkOrder.payment_status == models.WorkOrderPaymentStatus(payment_status))
    if responsible_staff:
        query = query.filter(models.WorkOrder.responsible_staff == responsible_staff)

    if date_str:
        try:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            query = query.filter(
                or_(
                    and_(models.WorkOrder.scheduled_at >= start_date, models.WorkOrder.scheduled_at < end_date),
                    and_(models.Booking.booking_time >= start_date, models.Booking.booking_time < end_date),
                )
            )
        except ValueError:
            raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD")

    if q:
        keyword = f"%{q.strip()}%"
        filters = [
            models.WorkOrder.customer_name.ilike(keyword),
            models.WorkOrder.customer_phone.ilike(keyword),
            models.WorkOrder.vehicle_license_plate.ilike(keyword),
            models.User.name.ilike(keyword),
            models.User.phone.ilike(keyword),
            models.Motor.license_plate.ilike(keyword),
        ]
        if q.strip().isdigit():
            numeric_q = int(q.strip())
            filters.extend([
                models.WorkOrder.id == numeric_q,
                models.WorkOrder.booking_id == numeric_q,
            ])
        query = query.filter(or_(*filters))

    return query.order_by(models.WorkOrder.created_at.desc()).offset(skip).limit(limit).all()

def create_work_order(db: Session, work_order: WorkOrderCreate):
    """
    建立工單。預約轉工單與現場工單共用此流程。
    """
    db_booking = None
    if work_order.booking_id:
        db_booking = get_booking(db, booking_id=work_order.booking_id)
        if not db_booking:
            raise ValueError(f"找不到預約單 ID={work_order.booking_id}")
        if db_booking.status in [
            models.BookingStatus.CANCELED,
            models.BookingStatus.NO_SHOW,
            models.BookingStatus.TIMEOUT,
            models.BookingStatus.SYSTEM_CLOSED,
        ]:
            raise ValueError("此預約狀態不可轉成工單")
        if db_booking.work_order:
            raise ValueError(f"此預約已建立工單 #{db_booking.work_order.id}")

    line_items = [_build_line_item(db, item) for item in work_order.line_items]
    if work_order.items:
        line_items.extend(_legacy_items_to_line_items(db, work_order.items))

    db_work_order = models.WorkOrder(
        booking_id=work_order.booking_id,
        service_type=work_order.service_type or models.WorkOrderServiceType.MAINTENANCE,
        problem_description=work_order.problem_description,
        inspection_result=work_order.inspection_result,
        responsible_staff=work_order.responsible_staff,
        scheduled_at=work_order.scheduled_at,
        notes=work_order.notes,
        line_items=line_items,
    )
    if db_booking:
        _hydrate_from_booking(db_work_order, db_booking)
        db_booking.status = models.BookingStatus.CONVERTED_TO_WORK_ORDER
        db.add(db_booking)
    else:
        _hydrate_direct_customer(db, db_work_order, work_order)

    _recalculate_work_order_total(db_work_order)
    _sync_payment_status(db_work_order)
    _sync_work_order_approvals(db_work_order)
    db.add(db_work_order)
    db.commit()
    return get_work_order(db, db_work_order.id)

def update_work_order(db: Session, work_order_id: int, work_order_update: WorkOrderUpdate):
    """
    更新工單資訊，主要用於更新狀態 (例如 '處理中' -> '已完成') 或備註。
    """
    db_work_order = get_work_order(db, work_order_id)
    if not db_work_order:
        return None

    update_data = _schema_dict(work_order_update, exclude_unset=True)
    line_items_data = update_data.pop("line_items", None)

    if line_items_data is not None:
        if any(item.inventory_deducted or (item.inventory_consumed_quantity or 0) > 0 for item in db_work_order.line_items):
            raise ValueError("已扣庫存的工單明細不可整批覆蓋，請用追加明細處理")
        _detach_work_order_purchase_requests(db, db_work_order)
        _release_work_order_inventory(db, db_work_order)
        db_work_order.line_items = [_build_line_item(db, WorkOrderLineItemCreate(**item)) for item in line_items_data]
        _recalculate_work_order_total(db_work_order)
        _sync_payment_status(db_work_order)
        _sync_work_order_approvals(db_work_order)

    for key, value in update_data.items():
        if key == "status":
            target_status = value
            if target_status == models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING:
                db_work_order.status = target_status
                _sync_work_order_approvals(db_work_order)
                continue
            if target_status in [
                models.WorkOrderStatus.AWAITING_PAYMENT,
                models.WorkOrderStatus.COMPLETED,
            ]:
                _request_inventory_consumption_approval(db_work_order)
            if target_status in APPROVAL_GATED_STATUSES:
                _sync_work_order_approvals(db_work_order)
                if _has_blocking_approval(db_work_order, target_status=target_status):
                    raise ValueError("此工單仍有待主管審核或被退回，不能進入後續狀態")
            if target_status == models.WorkOrderStatus.CANCELED:
                _detach_work_order_purchase_requests(db, db_work_order)
                _release_work_order_inventory(db, db_work_order)
            if target_status == models.WorkOrderStatus.COMPLETED and not _inventory_fully_consumed(db_work_order):
                raise ValueError("工單仍有零件 / 耗材尚未完成主管確認扣庫存，不能結案。")
            if target_status == models.WorkOrderStatus.COMPLETED and not db_work_order.completed_at:
                db_work_order.completed_at = datetime.utcnow()
        setattr(db_work_order, key, value)

    _recalculate_work_order_total(db_work_order)
    _sync_payment_status(db_work_order)
    _sync_work_order_approvals(db_work_order)
    
    db.add(db_work_order)
    db.commit()
    return get_work_order(db, work_order_id)


def soft_delete_work_order(db: Session, work_order_id: int, delete: WorkOrderDeleteCreate):
    db_work_order = get_work_order(db, work_order_id)
    if not db_work_order:
        return None
    if db_work_order.deleted_at:
        return db_work_order
    if db_work_order.payments or (db_work_order.paid_amount or 0) > 0:
        raise ValueError("已有付款紀錄的工單不可刪除，請改走退款或取消流程。")
    if any((item.inventory_consumed_quantity or 0) > 0 or item.inventory_deducted for item in db_work_order.line_items):
        raise ValueError("已有扣庫存紀錄的工單不可刪除，請改走庫存處理流程。")

    delete_data = _schema_dict(delete, exclude_unset=True)
    reason = (delete_data.get("reason") or "").strip()
    if not reason:
        raise ValueError("刪除原因為必填。")

    _detach_work_order_purchase_requests(db, db_work_order)
    _release_work_order_inventory(db, db_work_order)
    db_work_order.status = models.WorkOrderStatus.CANCELED
    db_work_order.deleted_at = datetime.utcnow()
    db_work_order.deleted_by = delete_data.get("actor")
    db_work_order.delete_reason = reason
    db.add(db_work_order)
    db.commit()
    return get_work_order(db, work_order_id)


def add_work_order_line_item(db: Session, work_order_id: int, item: WorkOrderLineItemCreate):
    db_work_order = get_work_order(db, work_order_id)
    if not db_work_order:
        return None
    db_item = _build_line_item(db, item)
    db_work_order.line_items.append(db_item)
    _recalculate_work_order_total(db_work_order)
    _sync_payment_status(db_work_order)
    _sync_work_order_approvals(db_work_order)
    db.commit()
    return get_work_order(db, work_order_id)


def add_work_order_payment(db: Session, work_order_id: int, payment: WorkOrderPaymentCreate):
    db_work_order = get_work_order(db, work_order_id)
    if not db_work_order:
        return None
    if payment.amount <= 0:
        raise ValueError("付款金額需大於 0")
    payment_data = _schema_dict(payment, exclude_unset=True)
    if not payment_data.get("paid_at"):
        payment_data["paid_at"] = datetime.utcnow()
    db_payment = models.WorkOrderPayment(**payment_data)
    db_work_order.payments.append(db_payment)
    db.flush()
    accounting_service.record_work_order_payment(db, db_work_order, db_payment)
    _sync_payment_status(db_work_order)
    if (
        db_work_order.payment_status == models.WorkOrderPaymentStatus.PAID
        and db_work_order.status == models.WorkOrderStatus.AWAITING_PAYMENT
        and _inventory_fully_consumed(db_work_order)
    ):
        db_work_order.status = models.WorkOrderStatus.COMPLETED
        db_work_order.completed_at = db_work_order.completed_at or datetime.utcnow()
    elif (
        db_work_order.payment_status == models.WorkOrderPaymentStatus.PAID
        and db_work_order.status == models.WorkOrderStatus.AWAITING_PAYMENT
    ):
        _request_inventory_consumption_approval(db_work_order)
    db.commit()
    return get_work_order(db, work_order_id)


def get_work_order_approvals(db: Session, status: str = None, skip: int = 0, limit: int = 100):
    query = (
        db.query(models.WorkOrderApproval)
        .options(joinedload(models.WorkOrderApproval.work_order))
    )
    if status:
        query = query.filter(models.WorkOrderApproval.status == models.WorkOrderApprovalStatus(status))
    return query.order_by(models.WorkOrderApproval.requested_at.asc()).offset(skip).limit(limit).all()


def review_work_order_approval(
    db: Session,
    approval_id: int,
    review: WorkOrderApprovalReview,
    approved: bool,
):
    db_approval = db.query(models.WorkOrderApproval).filter(models.WorkOrderApproval.id == approval_id).first()
    if not db_approval:
        return None
    db_approval.status = models.WorkOrderApprovalStatus.APPROVED if approved else models.WorkOrderApprovalStatus.REJECTED
    db_approval.reviewed_by = review.reviewed_by
    db_approval.note = review.note
    db_approval.reviewed_at = datetime.utcnow()

    if approved and db_approval.work_order:
        if db_approval.type == models.WorkOrderApprovalType.INVENTORY_RESERVATION:
            _reserve_work_order_inventory(db, db_approval.work_order, actor=review.reviewed_by)
        elif db_approval.type == models.WorkOrderApprovalType.INVENTORY_CONSUMPTION:
            _consume_work_order_inventory(db, db_approval.work_order, actor=review.reviewed_by)
            if (
                db_approval.work_order.status == models.WorkOrderStatus.AWAITING_PAYMENT
                and db_approval.work_order.payment_status == models.WorkOrderPaymentStatus.PAID
                and _inventory_fully_consumed(db_approval.work_order)
            ):
                db_approval.work_order.status = models.WorkOrderStatus.COMPLETED
                db_approval.work_order.completed_at = db_approval.work_order.completed_at or datetime.utcnow()

    db.commit()
    db.refresh(db_approval)
    return db_approval

from schemas.motor import MotorUpdate
from schemas.guest_customer import GuestMotorCreate, GuestMotorUpdate

# =================================================================
# Motor CRUD (車籍相關)
# =================================================================

def get_motor(db: Session, motor_id: int):
    """
    根據 ID 獲取單一車籍資料。
    """
    return db.query(models.Motor).filter(models.Motor.id == motor_id).first()

def update_motor(db: Session, motor_id: int, motor_update: MotorUpdate):
    """
    根據 ID 更新指定的車籍資料。
    """
    db_motor = get_motor(db, motor_id=motor_id)
    if not db_motor:
        return None
    
    # 獲取所有前端有提供的欄位值
    update_data = motor_update.dict(exclude_unset=True)
    
    # 遍歷所有要更新的欄位，並更新到資料庫物件上
    for key, value in update_data.items():
        setattr(db_motor, key, value)
        
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor


def get_guest_motor(db: Session, guest_motor_id: int):
    return db.query(models.GuestMotor).filter(models.GuestMotor.id == guest_motor_id).first()


def create_guest_motor(db: Session, guest_id: int, motor_in: GuestMotorCreate):
    guest = db.query(models.GuestCustomer).filter(models.GuestCustomer.id == guest_id).first()
    if not guest:
        return None

    existing = (
        db.query(models.GuestMotor)
        .filter(
            models.GuestMotor.guest_customer_id == guest_id,
            models.GuestMotor.license_plate == motor_in.license_plate,
            models.GuestMotor.status.is_(None),
        )
        .first()
    )
    if existing:
        for key, value in _schema_dict(motor_in, exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    db_motor = models.GuestMotor(guest_customer_id=guest_id, **_schema_dict(motor_in))
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor


def update_guest_motor(db: Session, guest_motor_id: int, motor_update: GuestMotorUpdate):
    db_motor = get_guest_motor(db, guest_motor_id=guest_motor_id)
    if not db_motor:
        return None
    for key, value in _schema_dict(motor_update, exclude_unset=True).items():
        setattr(db_motor, key, value)
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor

def delete_motor(db: Session, motor_id: int):
    """
    根據 ID 軟刪除指定的車籍資料。
    會將車輛的 status 設為 '已刪除'，而不是真的從資料庫移除。
    """
    db_motor = get_motor(db, motor_id=motor_id)
    if not db_motor:
        # 如果找不到，可以直接回傳 None，讓 endpoint 處理 404
        return None 
    
    # 執行軟刪除
    db_motor.status = "已刪除"
    db.add(db_motor)
    db.commit()
    db.refresh(db_motor)
    return db_motor



# =================================================================
# Booking CRUD (預約單相關)
# =================================================================

from schemas.booking import BookingCreate, BookingUpdate

def get_booking(db: Session, booking_id: int):
    """
    根據 ID 獲取單一預約單。
    """
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()

def get_bookings(db: Session, skip: int = 0, limit: int = 100, date_str: str = None):
    """
    獲取預約單列表，支援分頁與日期篩選。預設按預約時間倒序排列。
    """
    query = db.query(models.Booking).options(
        joinedload(models.Booking.user),
        joinedload(models.Booking.motor),
        joinedload(models.Booking.work_order),
    )
    if date_str:
        from datetime import datetime, timedelta
        try:
            start_date = datetime.strptime(date_str, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            query = query.filter(models.Booking.booking_time >= start_date, models.Booking.booking_time < end_date)
        except ValueError:
            pass
    return query.order_by(models.Booking.booking_time.desc()).offset(skip).limit(limit).all()

from datetime import datetime, timedelta

def get_bookings_by_date(db: Session, date_str: str):
    """
    獲取特定日期的預約單列表
    date_str 格式為 'YYYY-MM-DD'
    """
    try:
        start_date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
        
        return db.query(models.Booking).filter(
            models.Booking.booking_time >= start_date,
            models.Booking.booking_time < end_date,
            models.Booking.status.in_([
                models.BookingStatus.PENDING,
                models.BookingStatus.CONFIRMED,
                models.BookingStatus.ARRIVED,
                models.BookingStatus.CONVERTED_TO_WORK_ORDER,
                models.BookingStatus.SYSTEM_CLOSED,
            ])
        ).all()
    except ValueError:
        raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD")

def create_booking(db: Session, booking: BookingCreate, force: bool = False, is_system_close: bool = False):
    """
    建立一筆新的預約紀錄。
    在建立前會進行驗證，確保使用者和車籍資料存在且匹配。
    """
    # 驗證使用者是否存在
    db_user = get_user(db, google_id=booking.google_id)
    if not db_user:
        raise ValueError(f"找不到 Google ID 為 '{booking.google_id}' 的使用者。")

    # 驗證車籍資料是否存在
    db_motor = get_motor(db, motor_id=booking.motor_id)
    if not db_motor:
        raise ValueError(f"找不到 ID 為 {booking.motor_id} 的車籍資料。")

    # 驗證該車輛是否屬於該使用者
    if db_motor.google_id != db_user.google_id:
        raise ValueError(f"車籍資料 (ID: {booking.motor_id}) 與使用者 (Google ID: {booking.google_id}) 不匹配。")

    # 若非強制寫入，需檢查該時段是否已滿或被關閉
    if not force:
        existing_booking = db.query(models.Booking).filter(
            models.Booking.booking_time == booking.booking_time,
            models.Booking.status.in_([
                models.BookingStatus.PENDING,
                models.BookingStatus.CONFIRMED,
                models.BookingStatus.ARRIVED,
                models.BookingStatus.CONVERTED_TO_WORK_ORDER,
                models.BookingStatus.SYSTEM_CLOSED,
            ])
        ).first()
        if existing_booking:
            if existing_booking.status == models.BookingStatus.SYSTEM_CLOSED:
                raise ValueError(f"您選擇的時段目前為不開放。")
            else:
                raise ValueError(f"您選擇的時段已被預約，請選擇其他時段。")

    # 提供如果是系統關閉的狀態設定
    new_status = models.BookingStatus.SYSTEM_CLOSED if is_system_close else models.BookingStatus.PENDING

    # 移除傳入 model 的額外屬性（如 AdminBookingCreate 帶進來的 force）
    booking_dict = booking.dict()
    if 'force' in booking_dict:
        del booking_dict['force']

    # 將 Pydantic 模型轉換為 SQLAlchemy 模型，並設定狀態
    db_booking = models.Booking(
        **booking_dict,
        status=new_status
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking

def update_booking(db: Session, booking_id: int, booking_update: BookingUpdate):
    """
    更新預約單資訊，主要用於更新狀態或備註。
    """
    db_booking = get_booking(db, booking_id=booking_id)
    if not db_booking:
        return None

    # 獲取有被前端明確給定的值
    update_data = booking_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_booking, key, value)

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking
