from fastapi import APIRouter

from .endpoints import (
    accounting,
    admin,
    admins,
    announcements,
    auth,
    bookings,
    customers,
    guest_customers,
    inventory,
    motors,
    orders,
    points,
    portfolio,
    products,
    purchases,
    settings,
    users,
    work_orders,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(guest_customers.router, prefix="/guest-customers", tags=["Guest Customers"])
api_router.include_router(motors.router, prefix="/motors", tags=["Motors"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["Work Orders"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(points.router, prefix="/points", tags=["Points"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(inventory.router, prefix="/admin/inventory", tags=["Inventory"])
api_router.include_router(purchases.router, prefix="/admin/purchases", tags=["Purchases"])
api_router.include_router(accounting.router, prefix="/admin/accounting", tags=["Accounting"])
api_router.include_router(admins.router, prefix="/admins", tags=["Admin Accounts"])
api_router.include_router(announcements.router, prefix="/announcements", tags=["Announcements"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
