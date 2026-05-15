import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    try:
        with engine.connect() as conn:
            # check if column exists 
            result = conn.execute(text("SHOW COLUMNS FROM users LIKE '店家註記'"))
            if not result.fetchone():
                print("Adding '店家註記' column to users table...")
                # Note: PyMySQL + SQLAlchemy handles the connection. We execute the ALTER TABLE.
                conn.execute(text('ALTER TABLE users ADD COLUMN `店家註記` TEXT'))
                # SQLAlchemy 2.x requires commit for connection level statements if not autocommit
                try:
                    conn.commit()
                except AttributeError:
                    pass # SQLAlchemy 1.4 connection doesn't have commit()
                print("Column added successfully.")
            else:
                print("'店家註記' column already exists.")
    except Exception as e:
        print(f"Error patching database: {e}")

if __name__ == "__main__":
    patch_db()
