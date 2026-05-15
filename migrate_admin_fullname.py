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
            result = conn.execute(text("SHOW COLUMNS FROM admins LIKE 'full_name'"))
            if not result.fetchone():
                conn.execute(text("ALTER TABLE admins ADD COLUMN full_name VARCHAR(50) AFTER username"))
                conn.commit()
                print("Successfully added 'full_name' column to 'admins' table.")
            else:
                print("'full_name' column already exists.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
