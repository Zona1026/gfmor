import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from db.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SHOW COLUMNS FROM admins LIKE 'role'"))
            if not result.fetchone():
                print("Adding 'role' column to 'admins' table...")
                conn.execute(text("ALTER TABLE admins ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT '一般' COMMENT '管理員權限：最高級, 管理層, 一般' AFTER full_name"))
                conn.commit()
                print("Successfully added 'role' column.")
                
                # Update existing admins to have the '最高級' role initially
                print("Updating existing admins to '最高級'...")
                conn.execute(text("UPDATE admins SET role = '最高級'"))
                conn.commit()
                print("Successfully updated existing admins.")
            else:
                print("'role' column already exists in 'admins' table.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
