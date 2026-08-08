# 引入 SQLAlchemy 的必要模組
from sqlalchemy import (Column, Integer, String, Enum, DateTime, ForeignKey, Text, func, and_)
from sqlalchemy.orm import relationship

# 引入我們在 db/database.py 中建立的 Base
from .database import Base

# 為了讓 Python 的 Enum 與資料庫的 ENUM 類型能更好地配合
import enum

# 定義與資料庫 users.類別 對應的 Enum
class UserCategory(str, enum.Enum):
    MEMBER = "MEMBER"
    ADMIN = "ADMIN"

# 定義與資料庫 bookings.類別 對應的 Enum
class BookingCategory(str, enum.Enum):
    REPAIR = "REPAIR"
    MAINTENANCE = "MAINTENANCE"
    CONSULTATION = "CONSULTATION"

# 定義與資料庫 bookings.狀態 對應的 Enum
class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ARRIVED = "ARRIVED"
    CONVERTED_TO_WORK_ORDER = "CONVERTED_TO_WORK_ORDER"
    CANCELED = "CANCELED"
    NO_SHOW = "NO_SHOW"
    TIMEOUT = "TIMEOUT"
    COMPLETED = "COMPLETED"
    SYSTEM_OPEN = "SYSTEM_OPEN"
    SYSTEM_CLOSED = "SYSTEM_CLOSED"

# 定義與資料庫 orders.status 對應的 Enum
class OrderStatus(str, enum.Enum):
    PENDING = 'PENDING'
    DEPOSIT_PAID = 'DEPOSIT_PAID'
    FULL_PAID = 'FULL_PAID'
    COMPLETED = 'COMPLETED'
    CANCELED = 'CANCELED'

class OrderPaymentStatus(str, enum.Enum):
    PENDING = 'PENDING'
    VERIFYING = 'VERIFYING'
    PAID = 'PAID'
    FAILED = 'FAILED'
    PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED'
    REFUNDED = 'REFUNDED'
    CANCELED = 'CANCELED'

# 定義與資料庫 order_items.status 對應的 Enum
class OrderItemStatus(str, enum.Enum):
    NOT_ORDERED = 'NOT_ORDERED'
    ORDERED = 'ORDERED'
    ARRIVED_NEED_NOTIFY = 'ARRIVED_NEED_NOTIFY'
    NOTIFIED = 'NOTIFIED'
    COMPLETED = 'COMPLETED'

class PointTransactionType(str, enum.Enum):
    EARN = 'EARN'
    REDEEM = 'REDEEM'
    EXPIRE = 'EXPIRE'
    REFUND_ADJUST = 'REFUND_ADJUST'

# 定義與資料庫 work_orders.status 對應的 Enum
class WorkOrderStatus(str, enum.Enum):
    PENDING = 'PENDING'
    INSPECTION_PENDING = 'INSPECTION_PENDING'
    QUOTE_PENDING = 'QUOTE_PENDING'
    CUSTOMER_CONFIRMATION_PENDING = 'CUSTOMER_CONFIRMATION_PENDING'
    SUPERVISOR_APPROVAL_PENDING = 'SUPERVISOR_APPROVAL_PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'
    COMPLETED = 'COMPLETED'
    CANCELED = 'CANCELED'

class WorkOrderServiceType(str, enum.Enum):
    REPAIR = 'REPAIR'
    MAINTENANCE = 'MAINTENANCE'
    MODIFICATION = 'MODIFICATION'

class WorkOrderPaymentStatus(str, enum.Enum):
    UNPAID = 'UNPAID'
    PARTIALLY_PAID = 'PARTIALLY_PAID'
    PAID = 'PAID'
    REFUNDED = 'REFUNDED'

class AccountingSourceType(str, enum.Enum):
    WORK_ORDER = 'WORK_ORDER'
    SHOP_ORDER = 'SHOP_ORDER'
    PAYABLE = 'PAYABLE'

class PayableStatus(str, enum.Enum):
    UNPAID = 'UNPAID'
    PARTIALLY_PAID = 'PARTIALLY_PAID'
    PAID = 'PAID'
    CANCELED = 'CANCELED'

class WorkOrderLineItemType(str, enum.Enum):
    SERVICE = 'SERVICE'
    PART = 'PART'
    LABOR = 'LABOR'
    DISCOUNT = 'DISCOUNT'

class WorkOrderApprovalStatus(str, enum.Enum):
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'

class WorkOrderApprovalType(str, enum.Enum):
    DISCOUNT = 'DISCOUNT'
    HIGH_QUOTE = 'HIGH_QUOTE'
    STATUS_CHANGE = 'STATUS_CHANGE'
    INVENTORY_RESERVATION = 'INVENTORY_RESERVATION'
    INVENTORY_CONSUMPTION = 'INVENTORY_CONSUMPTION'

class InventoryType(str, enum.Enum):
    SHOP = 'SHOP'
    PART = 'PART'
    BOTH = 'BOTH'

class InventoryReservationStatus(str, enum.Enum):
    ACTIVE = 'ACTIVE'
    CONSUMED = 'CONSUMED'
    RELEASED = 'RELEASED'

class InventoryMovementType(str, enum.Enum):
    MANUAL_ADJUST = 'MANUAL_ADJUST'
    SHOP_ORDER_CONSUME = 'SHOP_ORDER_CONSUME'
    WORK_ORDER_CONSUME = 'WORK_ORDER_CONSUME'
    INSTORE_SALE = 'INSTORE_SALE'
    CANCEL_RESTORE = 'CANCEL_RESTORE'
    PURCHASE_RECEIPT = 'PURCHASE_RECEIPT'
    SCRAP_OUT = 'SCRAP_OUT'

class PurchaseRequestStatus(str, enum.Enum):
    PENDING_ORDER = 'PENDING_ORDER'
    ORDERED = 'ORDERED'
    PARTIAL_ARRIVED = 'PARTIAL_ARRIVED'
    ARRIVED_PENDING_ASSIGNMENT = 'ARRIVED_PENDING_ASSIGNMENT'
    ASSIGNED_TO_WORK_ORDER = 'ASSIGNED_TO_WORK_ORDER'
    CANCELED = 'CANCELED'

class Admin(Base):
    """
    管理員資料表模型 (對應 admins)
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    full_name = Column(String(50), nullable=True)
    role = Column(String(20), nullable=False, server_default="一般", comment="管理員權限：最高級, 管理層, 一般")
    hashed_password = Column(String(255), nullable=False)
    password_reset_token_hash = Column(String(64), unique=True, nullable=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)
    password_reset_requested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Announcement(Base):
    """
    公告資料表模型 (對應 announcements)
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="公告標題")
    description = Column(Text, nullable=True, comment="公告描述")
    image_url = Column(String(500), nullable=False, comment="Cloudinary 圖片網址")
    cloudinary_public_id = Column(String(255), nullable=True, comment="Cloudinary 圖片 ID，用於刪除")
    sort_order = Column(Integer, default=0, comment="排序權重，越小越前面")
    is_active = Column(Integer, default=1, comment="是否啟用：1=啟用, 0=停用")
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    """
    使用者資料表模型 (對應 users)
    """
    __tablename__ = "users"

    google_id = Column("Google ID", String(255), primary_key=True, index=True)
    name = Column("車主姓名", String(10), nullable=False)
    phone = Column("電話", String(10))
    email = Column("email", String(100), unique=True, index=True, nullable=False)
    category = Column("類別", Enum(UserCategory), default=UserCategory.MEMBER)
    join_time = Column("加入時間", DateTime, server_default=func.now())
    membership_level = Column("會員等級", String(45))
    cumulative_consumption = Column("累積消費", Integer)
    avatar = Column("頭像", String(255), nullable=True)
    admin_notes = Column("店家註記", Text, nullable=True)
    
    # 建立與其他資料表的關聯
    # 透過 primaryjoin，這個關聯只會找到未被軟刪除 (status 為 NULL) 的車輛
    motors = relationship(
        "Motor",
        primaryjoin=f"and_(User.google_id == Motor.google_id, Motor.status.is_(None))",
        back_populates="owner"
    )
    bookings = relationship("Booking", back_populates="user")
    orders = relationship("Order", back_populates="user")
    point_transactions = relationship("PointTransaction", back_populates="user")
    work_orders = relationship("WorkOrder", back_populates="user")

class GuestCustomer(Base):
    """
    散客客戶資料表模型 (對應 guest_customers)
    用於保存未註冊會員的現場消費客戶資料。
    """
    __tablename__ = "guest_customers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="散客姓名")
    phone = Column(String(20), nullable=False, index=True, comment="散客電話")
    notes = Column(Text, nullable=True, comment="店家備註")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    orders = relationship("Order", back_populates="guest_customer")
    motors = relationship("GuestMotor", back_populates="guest_customer", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="guest_customer")

class Product(Base):
    """
    商品資料表模型 (對應 products)
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="品名")
    description = Column(Text, comment="描述")
    price = Column(Integer, nullable=False, comment="價格")
    stock = Column(Integer, nullable=False, default=0, comment="庫存數量")
    inventory_type = Column(Enum(InventoryType), nullable=False, default=InventoryType.BOTH, server_default='BOTH', index=True)
    low_stock_threshold = Column(Integer, nullable=False, default=5, server_default='5')
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True, index=True)
    category = Column(String(50), comment="分類")
    image_url = Column(String(500), nullable=True, comment="商品圖片 URL")
    cloudinary_public_id = Column(String(255), nullable=True, comment="Cloudinary 圖片 ID")
    is_active = Column(Integer, default=1, comment="是否上架：1=上架, 0=下架")
    created_at = Column(DateTime, server_default=func.now())

    category_info = relationship("ProductCategory", back_populates="products")
    inventory_reservations = relationship("InventoryReservation", back_populates="product", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", back_populates="product")
    purchase_requests = relationship("PurchaseRequest", back_populates="product")
    # 建立與 WorkOrderItem 的一對多關聯
    work_order_items = relationship("WorkOrderItem", back_populates="product")

    @property
    def reserved_stock(self):
        return sum(
            reservation.quantity or 0
            for reservation in self.inventory_reservations
            if reservation.status == InventoryReservationStatus.ACTIVE
        )

    @property
    def available_stock(self):
        return max(0, (self.stock or 0) - self.reserved_stock)

class ProductCategory(Base):
    """
    商品分類主檔 (對應 product_categories)
    """
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    products = relationship("Product", back_populates="category_info")

class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    status = Column(Enum(InventoryReservationStatus), nullable=False, default=InventoryReservationStatus.ACTIVE, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    actor = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="inventory_reservations")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    movement_type = Column(Enum(InventoryMovementType), nullable=False, index=True)
    quantity_delta = Column(Integer, nullable=False)
    stock_before = Column(Integer, nullable=False)
    stock_after = Column(Integer, nullable=False)
    source_type = Column(String(50), nullable=True, index=True)
    source_id = Column(Integer, nullable=True, index=True)
    actor = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    product = relationship("Product", back_populates="inventory_movements")

class Motor(Base):
    """
    車籍資料表模型 (對應 motor)
    """
    __tablename__ = "motor"
    id = Column("ID", Integer, primary_key=True, index=True, autoincrement=True)
    google_id = Column("Google ID", String(255), ForeignKey("users.Google ID"), nullable=False)
    license_plate = Column("車牌", String(45), nullable=False, unique=True, index=True) # 車牌應為唯一
    brand = Column("廠牌", String(45))
    model_name = Column("型號", String(45)) # 欄位名稱從「車種」改為「型號」以符合 schema
    vin = Column("引擎號碼", String(45), unique=True) # 引擎號碼應為唯一
    mileage = Column("里程數", Integer)
    status = Column("狀態", String(45), nullable=True, index=True, comment="用於軟刪除，正常為 NULL，刪除為 '已刪除'")
    
    owner = relationship("User", back_populates="motors")
    bookings = relationship("Booking", back_populates="motor")
    work_orders = relationship("WorkOrder", back_populates="motor")

class GuestMotor(Base):
    """
    散客車輛資料表模型 (對應 guest_motors)
    用於保存未註冊會員的現場服務車輛資料。
    """
    __tablename__ = "guest_motors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    guest_customer_id = Column(Integer, ForeignKey("guest_customers.id"), nullable=False, index=True)
    license_plate = Column(String(45), nullable=False, index=True)
    brand = Column(String(45), nullable=True)
    model_name = Column(String(45), nullable=True)
    vin = Column(String(45), nullable=True)
    mileage = Column(Integer, nullable=True)
    status = Column(String(45), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    guest_customer = relationship("GuestCustomer", back_populates="motors")
    work_orders = relationship("WorkOrder", back_populates="guest_motor")

class Booking(Base):
    """
    預約紀錄資料表模型 (對應 bookings)
    """
    __tablename__ = "bookings"
    id = Column("預約單號", Integer, primary_key=True, autoincrement=True)
    google_id = Column("Google ID", String(255), ForeignKey("users.Google ID"), nullable=False)
    motor_id = Column("車籍ID", Integer, ForeignKey("motor.ID"), nullable=False)
    booking_time = Column("預約時間", DateTime, nullable=False)
    category = Column("類別", Enum(BookingCategory), nullable=False)
    created_at = Column("預約單成立時間", DateTime, server_default=func.now())
    status = Column("狀態", Enum(BookingStatus), nullable=False)
    notes = Column("備註", String(100))
    
    # 建立與 User (使用者) 的多對一關聯
    user = relationship("User", back_populates="bookings")
    # 建立與 Motor (車籍) 的多對一關聯
    motor = relationship("Motor", back_populates="bookings")
    # 建立與 WorkOrder (工單) 的一對一關聯
    work_order = relationship("WorkOrder", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class Order(Base):
    """
    客戶訂單資料表模型 (對應 orders)
    """
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    google_id = Column(String(255), ForeignKey("users.Google ID"), nullable=True)
    guest_customer_id = Column(Integer, ForeignKey("guest_customers.id"), nullable=True, index=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    payment_status = Column(Enum(OrderPaymentStatus), nullable=False, default=OrderPaymentStatus.PENDING, index=True)
    source = Column(String(20), nullable=False, default='online', comment='訂單來源：online=線上、instore=現場')
    total_amount = Column(Integer, nullable=False)
    recipient_name = Column(String(50), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    shipping_address = Column(String(255), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    guest_customer = relationship("GuestCustomer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    point_transactions = relationship("PointTransaction", back_populates="order")
    payment_records = relationship("PaymentRecord", back_populates="order")
    refund_records = relationship("RefundRecord", back_populates="order")
    item_notifications = relationship("OrderItemNotification", back_populates="order")

    @property
    def customer_type(self):
        return "guest" if self.guest_customer_id else "member"

class OrderItem(Base):
    """
    訂單項目資料表模型 (對應 order_items)
    """
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    status = Column(Enum(OrderItemStatus), nullable=False, default=OrderItemStatus.NOT_ORDERED)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    notifications = relationship("OrderItemNotification", back_populates="order_item", cascade="all, delete-orphan")

    @property
    def latest_notification(self):
        if not self.notifications:
            return None
        return max(self.notifications, key=lambda notification: notification.id or 0)

class OrderItemNotification(Base):
    """
    訂單商品到貨通知紀錄。
    """
    __tablename__ = "order_item_notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    method = Column(String(50), nullable=False)
    recipient_name = Column(String(50), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    note = Column(Text, nullable=True)
    actor = Column(String(50), nullable=True)
    notified_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    order_item = relationship("OrderItem", back_populates="notifications")
    order = relationship("Order", back_populates="item_notifications")

class PointTransaction(Base):
    """
    會員點數流水帳。
    EARN 會保留 remaining_points 和 expires_at，退款、到期、折抵則以負數交易扣回。
    """
    __tablename__ = "point_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    google_id = Column(String(255), ForeignKey("users.Google ID"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    type = Column(Enum(PointTransactionType), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    remaining_points = Column(Integer, nullable=False, default=0)
    issued_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=True, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="point_transactions")
    order = relationship("Order", back_populates="point_transactions")

class WorkOrder(Base):
    """
    工單資料表模型 (對應 work_orders)
    這個模型用來記錄每一筆維修或改裝工作的詳細資訊。
    """
    __tablename__ = "work_orders"

    # 工單的唯一流水號，作為主鍵
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 關聯到對應的預約單；現場工單可不綁預約
    booking_id = Column(Integer, ForeignKey("bookings.預約單號"), nullable=True, unique=True)
    google_id = Column(String(255), ForeignKey("users.Google ID"), nullable=True, index=True)
    guest_customer_id = Column(Integer, ForeignKey("guest_customers.id"), nullable=True, index=True)
    guest_motor_id = Column(Integer, ForeignKey("guest_motors.id"), nullable=True, index=True)
    motor_id = Column(Integer, ForeignKey("motor.ID"), nullable=True, index=True)
    customer_name = Column(String(50), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    vehicle_license_plate = Column(String(45), nullable=True, index=True)
    vehicle_brand = Column(String(45), nullable=True)
    vehicle_model = Column(String(45), nullable=True)
    vehicle_vin = Column(String(45), nullable=True)
    vehicle_mileage = Column(Integer, nullable=True)
    service_type = Column(Enum(WorkOrderServiceType), nullable=False, default=WorkOrderServiceType.MAINTENANCE)
    problem_description = Column(Text, nullable=True)
    inspection_result = Column(Text, nullable=True)
    # 工單目前的處理狀態，使用預先定義好的 Enum
    status = Column(Enum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.INSPECTION_PENDING)
    payment_status = Column(Enum(WorkOrderPaymentStatus), nullable=False, default=WorkOrderPaymentStatus.UNPAID)
    responsible_staff = Column(String(50), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    # 這張工單的總金額，包含所有商品和服務
    total_amount = Column(Integer, nullable=False, default=0)
    # 技師或管理員可填寫的內部備註
    notes = Column(Text, nullable=True)
    # 工單的建立時間，資料庫會自動填入現在的時間
    created_at = Column(DateTime, server_default=func.now())
    # 工單的完成時間，預設為空，當工單狀態變為「已完成」時才填入
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(50), nullable=True)
    delete_reason = Column(Text, nullable=True)

    # 建立與 Booking (預約) 的一對一關聯
    # work_order 透過 booking_id 找到對應的 booking 紀錄
    booking = relationship("Booking", back_populates="work_order")
    user = relationship("User", back_populates="work_orders")
    guest_customer = relationship("GuestCustomer", back_populates="work_orders")
    guest_motor = relationship("GuestMotor", back_populates="work_orders")
    motor = relationship("Motor", back_populates="work_orders")
    # 建立與 WorkOrderItem (工單項目) 的一對多關聯
    # 當刪除一張工單時，與它關聯的所有工單項目也會被一併刪除 (cascade)
    items = relationship("WorkOrderItem", back_populates="work_order", cascade="all, delete-orphan")
    line_items = relationship("WorkOrderLineItem", back_populates="work_order", cascade="all, delete-orphan")
    payments = relationship("WorkOrderPayment", back_populates="work_order", cascade="all, delete-orphan")
    approvals = relationship("WorkOrderApproval", back_populates="work_order", cascade="all, delete-orphan")
    purchase_requests = relationship("PurchaseRequest", back_populates="work_order")
    payment_records = relationship("PaymentRecord", back_populates="work_order")
    refund_records = relationship("RefundRecord", back_populates="work_order")

    @property
    def paid_amount(self):
        return sum(payment.amount or 0 for payment in self.payments)

    @property
    def balance_amount(self):
        return max(0, (self.total_amount or 0) - self.paid_amount)

    @property
    def customer_type(self):
        return "guest" if self.guest_customer_id else "member"

    @property
    def approval_status(self):
        pending = [item for item in self.approvals if item.status == WorkOrderApprovalStatus.PENDING]
        if pending:
            return WorkOrderApprovalStatus.PENDING
        approved = [item for item in self.approvals if item.status == WorkOrderApprovalStatus.APPROVED]
        if approved:
            return WorkOrderApprovalStatus.APPROVED
        rejected = [item for item in self.approvals if item.status == WorkOrderApprovalStatus.REJECTED]
        if rejected:
            return WorkOrderApprovalStatus.REJECTED
        return None

    @property
    def inventory_reservation_pending(self):
        return any(
            approval.type == WorkOrderApprovalType.INVENTORY_RESERVATION
            and approval.status == WorkOrderApprovalStatus.PENDING
            for approval in self.approvals
        )

    @property
    def inventory_consumption_pending(self):
        return any(
            approval.type == WorkOrderApprovalType.INVENTORY_CONSUMPTION
            and approval.status == WorkOrderApprovalStatus.PENDING
            for approval in self.approvals
        )

    @property
    def inventory_reserved(self):
        return any(
            item.type == WorkOrderLineItemType.PART
            and item.product_id
            and (item.inventory_reserved_quantity or 0) > 0
            for item in self.line_items
        )

    @property
    def inventory_consumed(self):
        part_items = [
            item for item in self.line_items
            if item.type == WorkOrderLineItemType.PART and item.product_id
        ]
        return bool(part_items) and all(
            (item.inventory_consumed_quantity or 0) >= (item.quantity or 0)
            for item in part_items
        )

class WorkOrderItem(Base):
    """
    工單項目詳情資料表模型 (對應 work_order_items)
    這個模型用來記錄每一張工單中，具體使用了哪些商品、數量以及當時的價格。
    """
    __tablename__ = "work_order_items"

    # 工單項目的唯一流水號，作為主鍵
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 關聯到此項目屬於哪一張工單
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    # 關聯到此項目使用了資料庫中的哪一個商品
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    # 記錄該商品在此工單中的使用數量
    quantity = Column(Integer, nullable=False)
    # 記錄執行當下的商品單價，這是為了避免未來商品價格變動影響到歷史訂單的準確性
    unit_price = Column(Integer, nullable=False)

    # 建立與 WorkOrder (工單) 的多對一關聯
    # 多個 work_order_item 可以屬於同一個 work_order
    work_order = relationship("WorkOrder", back_populates="items")
    # 建立與 Product (商品) 的多對一關聯
    # 多個 work_order_item 可能會對應到同一個 product
    product = relationship("Product", back_populates="work_order_items")

class WorkOrderLineItem(Base):
    """
    結構化工單明細，包含施工項目、零件耗材、工資服務費與折扣。
    """
    __tablename__ = "work_order_line_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False, index=True)
    type = Column(Enum(WorkOrderLineItemType), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False, default=0)
    is_confirmed = Column(Integer, nullable=False, default=1)
    inventory_reserved_quantity = Column(Integer, nullable=False, default=0)
    inventory_consumed_quantity = Column(Integer, nullable=False, default=0)
    inventory_deducted = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())

    work_order = relationship("WorkOrder", back_populates="line_items")
    product = relationship("Product")
    purchase_requests = relationship("PurchaseRequest", back_populates="work_order_line_item")

    @property
    def line_total(self):
        return (self.quantity or 0) * (self.unit_price or 0)

    @property
    def inventory_shortage_quantity(self):
        return max(
            0,
            (self.quantity or 0)
            - (self.inventory_reserved_quantity or 0)
            - (self.inventory_consumed_quantity or 0),
        )

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True, index=True)
    work_order_line_item_id = Column(Integer, ForeignKey("work_order_line_items.id"), nullable=True, index=True)
    item_name = Column(String(100), nullable=False)
    customer_name = Column(String(50), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    vehicle_license_plate = Column(String(45), nullable=True)
    requested_quantity = Column(Integer, nullable=False)
    ordered_quantity = Column(Integer, nullable=False, default=0)
    arrived_quantity = Column(Integer, nullable=False, default=0)
    assigned_quantity = Column(Integer, nullable=False, default=0)
    status = Column(Enum(PurchaseRequestStatus), nullable=False, default=PurchaseRequestStatus.PENDING_ORDER, index=True)
    supplier_name = Column(String(100), nullable=True)
    expected_arrival_date = Column(DateTime, nullable=True)
    responsible_staff = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    product = relationship("Product", back_populates="purchase_requests")
    work_order = relationship("WorkOrder", back_populates="purchase_requests")
    work_order_line_item = relationship("WorkOrderLineItem", back_populates="purchase_requests")
    receipts = relationship("PurchaseReceipt", back_populates="purchase_request", cascade="all, delete-orphan")
    assignments = relationship("PurchaseAssignment", back_populates="purchase_request", cascade="all, delete-orphan")

    @property
    def unassigned_arrived_quantity(self):
        return max(0, (self.arrived_quantity or 0) - (self.assigned_quantity or 0))

class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    actor = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False, server_default=func.now())

    purchase_request = relationship("PurchaseRequest", back_populates="receipts")

class PurchaseAssignment(Base):
    __tablename__ = "purchase_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False, index=True)
    work_order_line_item_id = Column(Integer, ForeignKey("work_order_line_items.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    actor = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())

    purchase_request = relationship("PurchaseRequest", back_populates="assignments")

class WorkOrderPayment(Base):
    """
    工單付款紀錄，獨立於商城訂單付款。
    """
    __tablename__ = "work_order_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    method = Column(String(50), nullable=True)
    paid_at = Column(DateTime, nullable=False, server_default=func.now())
    note = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", back_populates="payments")
    payment_record = relationship("PaymentRecord", back_populates="work_order_payment", uselist=False)

class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_type = Column(Enum(AccountingSourceType), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    work_order_payment_id = Column(Integer, ForeignKey("work_order_payments.id"), nullable=True, index=True)
    customer_name = Column(String(50), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    amount = Column(Integer, nullable=False)
    method = Column(String(50), nullable=True)
    actor = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    work_order = relationship("WorkOrder", back_populates="payment_records")
    order = relationship("Order", back_populates="payment_records")
    work_order_payment = relationship("WorkOrderPayment", back_populates="payment_record")

class RefundRecord(Base):
    __tablename__ = "refund_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_type = Column(Enum(AccountingSourceType), nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    customer_name = Column(String(50), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    amount = Column(Integer, nullable=False)
    method = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    actor = Column(String(50), nullable=True)
    refunded_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    work_order = relationship("WorkOrder", back_populates="refund_records")
    order = relationship("Order", back_populates="refund_records")

class Payable(Base):
    __tablename__ = "payables"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier_name = Column(String(100), nullable=False)
    purchase_request_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=True, index=True)
    title = Column(String(120), nullable=False)
    amount = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(Enum(PayableStatus), nullable=False, default=PayableStatus.UNPAID, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    purchase_request = relationship("PurchaseRequest")
    payments = relationship("PayablePayment", back_populates="payable", cascade="all, delete-orphan")

    @property
    def paid_amount(self):
        return sum(payment.amount or 0 for payment in self.payments)

    @property
    def balance_amount(self):
        return max(0, (self.amount or 0) - self.paid_amount)

class PayablePayment(Base):
    __tablename__ = "payable_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    payable_id = Column(Integer, ForeignKey("payables.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    method = Column(String(50), nullable=True)
    actor = Column(String(50), nullable=True)
    note = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    payable = relationship("Payable", back_populates="payments")

class WorkOrderApproval(Base):
    """
    工單主管審核佇列。
    """
    __tablename__ = "work_order_approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False, index=True)
    type = Column(Enum(WorkOrderApprovalType), nullable=False)
    title = Column(String(120), nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(WorkOrderApprovalStatus), nullable=False, default=WorkOrderApprovalStatus.PENDING)
    requested_by = Column(String(50), nullable=True)
    reviewed_by = Column(String(50), nullable=True)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    work_order = relationship("WorkOrder", back_populates="approvals")

class PortfolioItem(Base):
    """
    作品集資料表模型 (對應 portfolio_items)
    """
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False, comment="作品標題")
    category = Column(String(50), nullable=False, index=True, comment="分類 (level-1~level-4)")
    description = Column(Text, nullable=True, comment="作品描述")
    image_url = Column(String(500), nullable=False, comment="Cloudinary 圖片網址")
    cloudinary_public_id = Column(String(255), nullable=True, comment="Cloudinary 圖片 ID")
    created_at = Column(DateTime, server_default=func.now())

class SystemSetting(Base):
    """
    系統設定資料表 (對應 system_settings)
    用於儲存店名、地址、電話、營業時間等全域資訊
    """
    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
