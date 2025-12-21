from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from .database import Base

# 1. 使用者 (User) - 新增等級與累積消費
class User(Base):
    __tablename__ = "users"

    google_id = Column("Google ID", String(255), primary_key=True, index=True)
    name = Column("車主姓名", String(10), nullable=False)
    phone = Column("電話", String(10), nullable=True)
    email = Column("email", String(100), nullable=False)
    role = Column("類別", String(20), default="MEMBER") 
    created_at = Column("加入時間", DateTime, default=func.now())
    
    # ★ 新增欄位 ★
    level = Column("會員等級", String(20), default="普卡會員")  # 普卡 / 銀卡 / 金卡
    total_spending = Column("累積消費", Integer, default=0)

# 2. 預約單 (Booking) - 保持不變
class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column("預約單號", Integer, primary_key=True, index=True, autoincrement=True)
    user_google_id = Column("Google ID", String(255), ForeignKey("users.Google ID"), nullable=False)
    car_model = Column("車種", String(45), nullable=False)
    booking_time = Column("預約時間", DateTime, nullable=False, index=True)
    category = Column("類別", String(20), nullable=False)
    created_at = Column("預約單成立時間", DateTime, default=func.now())
    status = Column("狀態", String(20), default="預約中")
    engine_no = Column("引擎號碼", String(15), nullable=True)
    note = Column("備註", String(100), nullable=True)

# 3. 管理員 (Admin) - 保持不變
class Admin(Base):
    __tablename__ = "admins"
    account_id = Column("帳號", Integer, primary_key=True) 
    password = Column("密碼", String(45))
    name = Column("名稱", String(45))
    role = Column("權限", String(10), default="一般")

# 4. 時段設定 (SlotConfiguration) - 保持不變
class SlotConfiguration(Base):
    __tablename__ = "slot_configurations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_time = Column("指定時間", DateTime, unique=True, index=True) 
    max_capacity = Column("最大人數", Integer, default=1)

# 5. ★ 新增：消費紀錄 (Consumption) ★
class Consumption(Base):
    __tablename__ = "consumptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_google_id = Column("Google ID", String(255), ForeignKey("users.Google ID"), nullable=False)
    amount = Column("消費金額", Integer, nullable=False)
    description = Column("消費項目", String(100), nullable=False) # 例如：換機油、維修
    created_at = Column("消費時間", DateTime, default=func.now())

# models.py (加在最下面)

# 修改原本的 Portfolio 類別
class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=False)
    image_url = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=func.now())