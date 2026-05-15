import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    with engine.connect() as conn:
        # Step 1: Check current enum values
        result = conn.execute(text("SHOW COLUMNS FROM orders WHERE Field='status'"))
        row = result.fetchone()
        print(f"Current status column: {row}")
        
        # Step 2: Check existing data
        result = conn.execute(text("SELECT DISTINCT status FROM orders"))
        statuses = [r[0] for r in result.fetchall()]
        print(f"Existing status values: {statuses}")

        # Step 3: First widen the enum to include both old and new values
        conn.execute(text("""
            ALTER TABLE orders MODIFY COLUMN status 
            VARCHAR(50) NOT NULL DEFAULT '未付款'
        """))
        
        # Step 4: Convert old values
        conn.execute(text("UPDATE orders SET status='未付款' WHERE status IN ('待處理','PENDING')"))
        conn.execute(text("UPDATE orders SET status='已結案' WHERE status IN ('已完成','COMPLETED','已出貨','SHIPPED','處理中','PROCESSING')"))
        conn.execute(text("UPDATE orders SET status='已取消' WHERE status IN ('CANCELED')"))
        
        # Step 5: Now set the final enum
        conn.execute(text("""
            ALTER TABLE orders MODIFY COLUMN status 
            ENUM('未付款','已付訂金未取貨','已付全款未取貨','已結案','已取消')
            NOT NULL DEFAULT '未付款'
        """))
        
        conn.commit()
        print("Done!")

if __name__ == "__main__":
    patch_db()
