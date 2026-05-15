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
    CANCELED = "CANCELED"
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

# 定義與資料庫 work_orders.status 對應的 Enum
class WorkOrderStatus(str, enum.Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    AWAITING_PAYMENT = 'AWAITING_PAYMENT'
    COMPLETED = 'COMPLETED'
    CANCELED = 'CANCELED'

class Admin(Base):
    """
    管理員資料表模型 (對應 admins)
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(50), nullable=True)
    hashed_password = Column(String(255), nullable=False)
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
    category = Column(String(50), comment="分類")
    image_url = Column(String(500), nullable=True, comment="商品圖片 URL")
    cloudinary_public_id = Column(String(255), nullable=True, comment="Cloudinary 圖片 ID")
    is_active = Column(Integer, default=1, comment="是否上架：1=上架, 0=下架")
    created_at = Column(DateTime, server_default=func.now())

    # 建立與 WorkOrderItem 的一對多關聯
    work_order_items = relationship("WorkOrderItem", back_populates="product")

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
    google_id = Column(String(255), ForeignKey("users.Google ID"), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    source = Column(String(20), nullable=False, default='online', comment='訂單來源：online=線上、instore=現場')
    total_amount = Column(Integer, nullable=False)
    recipient_name = Column(String(50), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    shipping_address = Column(String(255), nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

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

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class WorkOrder(Base):
    """
    工單資料表模型 (對應 work_orders)
    這個模型用來記錄每一筆維修或改裝工作的詳細資訊。
    """
    __tablename__ = "work_orders"

    # 工單的唯一流水號，作為主鍵
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # 關聯到對應的預約單，這是建立工單的來源
    booking_id = Column(Integer, ForeignKey("bookings.預約單號"), nullable=False, unique=True)
    # 工單目前的處理狀態，使用預先定義好的 Enum
    status = Column(Enum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.PENDING)
    # 這張工單的總金額，包含所有商品和服務
    total_amount = Column(Integer, nullable=False, default=0)
    # 技師或管理員可填寫的內部備註
    notes = Column(Text, nullable=True)
    # 工單的建立時間，資料庫會自動填入現在的時間
    created_at = Column(DateTime, server_default=func.now())
    # 工單的完成時間，預設為空，當工單狀態變為「已完成」時才填入
    completed_at = Column(DateTime, nullable=True)

    # 建立與 Booking (預約) 的一對一關聯
    # work_order 透過 booking_id 找到對應的 booking 紀錄
    booking = relationship("Booking", back_populates="work_order")
    # 建立與 WorkOrderItem (工單項目) 的一對多關聯
    # 當刪除一張工單時，與它關聯的所有工單項目也會被一併刪除 (cascade)
    items = relationship("WorkOrderItem", back_populates="work_order", cascade="all, delete-orphan")

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
