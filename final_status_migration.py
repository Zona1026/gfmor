import sys
import os
sys.path.append(os.getcwd())
from sqlalchemy import text
from db.database import engine

def migrate():
    with engine.connect() as conn:
        print("Migrating orders table...")
        # Convert Chinese to Latin names
        conn.execute(text("ALTER TABLE orders MODIFY COLUMN status VARCHAR(50)"))
        conn.execute(text("UPDATE orders SET status='PENDING' WHERE status='未付款'"))
        conn.execute(text("UPDATE orders SET status='DEPOSIT_PAID' WHERE status='已付訂金未取貨'"))
        conn.execute(text("UPDATE orders SET status='FULL_PAID' WHERE status='已付全款未取貨'"))
        conn.execute(text("UPDATE orders SET status='COMPLETED' WHERE status='已結案'"))
        conn.execute(text("UPDATE orders SET status='CANCELED' WHERE status='已取消'"))
        conn.execute(text("""
            ALTER TABLE orders MODIFY COLUMN status 
            ENUM('PENDING','DEPOSIT_PAID','FULL_PAID','COMPLETED','CANCELED') 
            NOT NULL DEFAULT 'PENDING'
        """))

        print("Migrating work_orders table...")
        # Same for work_orders
        conn.execute(text("ALTER TABLE work_orders MODIFY COLUMN status VARCHAR(50)"))
        conn.execute(text("UPDATE work_orders SET status='PENDING' WHERE status IN ('待處理','未處理')"))
        conn.execute(text("UPDATE work_orders SET status='IN_PROGRESS' WHERE status IN ('處理中','維修中')"))
        conn.execute(text("UPDATE work_orders SET status='AWAITING_PAYMENT' WHERE status IN ('待付款')"))
        conn.execute(text("UPDATE work_orders SET status='COMPLETED' WHERE status IN ('已完成','已結案')"))
        conn.execute(text("UPDATE work_orders SET status='CANCELED' WHERE status IN ('取消','已取消')"))
        conn.execute(text("""
            ALTER TABLE work_orders MODIFY COLUMN status 
            ENUM('PENDING','IN_PROGRESS','AWAITING_PAYMENT','COMPLETED','CANCELED') 
            NOT NULL DEFAULT 'PENDING'
        """))

        conn.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
