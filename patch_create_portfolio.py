import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'portfolio_items'"))
            if not result.fetchone():
                print("Creating 'portfolio_items' table...")
                conn.execute(text("""
                    CREATE TABLE portfolio_items (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(100) NOT NULL COMMENT '作品標題',
                        category VARCHAR(50) NOT NULL COMMENT '分類',
                        description TEXT COMMENT '作品描述',
                        image_url VARCHAR(500) NOT NULL COMMENT 'Cloudinary 圖片網址',
                        cloudinary_public_id VARCHAR(255) COMMENT 'Cloudinary 圖片 ID',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_category (category)
                    )
                """))
                conn.commit()
                print("Table created successfully.")
            else:
                print("'portfolio_items' table already exists.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    patch_db()
