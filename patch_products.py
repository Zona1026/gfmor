import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    try:
        with engine.connect() as conn:
            # Check if image_url column exists
            result = conn.execute(text("SHOW COLUMNS FROM products LIKE 'image_url'"))
            if not result.fetchone():
                print("Adding 'image_url' column...")
                conn.execute(text("ALTER TABLE products ADD COLUMN image_url VARCHAR(500) COMMENT '商品圖片 URL'"))
                
            result = conn.execute(text("SHOW COLUMNS FROM products LIKE 'cloudinary_public_id'"))
            if not result.fetchone():
                print("Adding 'cloudinary_public_id' column...")
                conn.execute(text("ALTER TABLE products ADD COLUMN cloudinary_public_id VARCHAR(255) COMMENT 'Cloudinary 圖片 ID'"))

            result = conn.execute(text("SHOW COLUMNS FROM products LIKE 'is_active'"))
            if not result.fetchone():
                print("Adding 'is_active' column...")
                conn.execute(text("ALTER TABLE products ADD COLUMN is_active INT DEFAULT 1 COMMENT '是否上架'"))

            conn.commit()
            print("Products table patched successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    patch_db()
