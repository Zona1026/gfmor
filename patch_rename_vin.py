import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    try:
        with engine.connect() as conn:
            # Check if old column exists
            result = conn.execute(text("SHOW COLUMNS FROM motor LIKE '車身號碼'"))
            if result.fetchone():
                print("Renaming '車身號碼' to '引擎號碼'...")
                conn.execute(text("ALTER TABLE motor CHANGE `車身號碼` `引擎號碼` VARCHAR(45)"))
                conn.commit()
                print("Column renamed successfully.")
            else:
                # Check if new column already exists
                result2 = conn.execute(text("SHOW COLUMNS FROM motor LIKE '引擎號碼'"))
                if result2.fetchone():
                    print("'引擎號碼' column already exists. No action needed.")
                else:
                    print("Neither column found. Something is wrong.")
    except Exception as e:
        print(f"Error patching database: {e}")

if __name__ == "__main__":
    patch_db()
