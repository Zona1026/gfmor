from fastapi import APIRouter
from .endpoints import products, work_orders, bookings, users, motors, auth, orders, admin, announcements, portfolio, admins

# 建立一個給 API v1 用的主 router
api_router = APIRouter()

# 將各個 endpoint 的 router 包含進來
# 這樣可以讓專案的 API 結構更有條理
api_router.include_router(auth.router, prefix="/auth", tags=["認證 (Authentication)"])
api_router.include_router(users.router, prefix="/users", tags=["使用者 (Users)"])
api_router.include_router(motors.router, prefix="/motors", tags=["車籍 (Motors)"])
api_router.include_router(products.router, prefix="/products", tags=["商品 (Products)"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["預約 (Bookings)"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["工單 (Work Orders)"])
api_router.include_router(orders.router, prefix="/orders", tags=["訂單 (Orders)"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理者 (Admin)"])
api_router.include_router(admins.router, prefix="/admins", tags=["管理者帳號管理 (Admin Accounts)"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["公告 (Announcements)"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["作品集 (Portfolio)"])
