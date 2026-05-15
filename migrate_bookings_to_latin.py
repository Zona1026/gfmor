import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from db.database import SessionLocal
from db import models
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        # 1. Migrate Booking Status
        status_map = {
            '預約中': 'PENDING',
            '預約取消': 'CANCELED',
            '已超時': 'TIMEOUT',
            '已結案': 'COMPLETED',
            '時段關閉': 'SYSTEM_CLOSED',
            '後台開放時間': 'SYSTEM_OPEN'
        }
        
        bookings = db.query(models.Booking).all()
        for b in bookings:
            # Check Status
            if b.status in status_map:
                old = b.status
                b.status = status_map[old]
                print(f"Updated Booking #{b.id} status: {old} -> {b.status}")
            
            # Check Category
            category_map = {
                '維修': 'REPAIR',
                '保養': 'MAINTENANCE',
                '諮詢': 'CONSULTATION'
            }
            if b.category in category_map:
                old = b.category
                b.category = category_map[old]
                print(f"Updated Booking #{b.id} category: {old} -> {b.category}")

        db.commit()
        print("Booking migration completed successfully (via ORM).")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
