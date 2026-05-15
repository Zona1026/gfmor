import sys
sys.path.append("d:/Python/GFmoter")
from sqlalchemy import text
from db.database import engine

def patch_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES LIKE 'announcements'"))
            if not result.fetchone():
                print("Creating 'announcements' table...")
                conn.execute(text("""
                    CREATE TABLE announcements (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(100) NOT NULL COMMENT '公告標題',
                        description TEXT COMMENT '公告描述',
                        image_url VARCHAR(500) NOT NULL COMMENT 'Cloudinary 圖片網址',
                        cloudinary_public_id VARCHAR(255) COMMENT 'Cloudinary 圖片 ID',
                        sort_order INT DEFAULT 0 COMMENT '排序權重',
                        is_active INT DEFAULT 1 COMMENT '是否啟用',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.commit()
                print("Table created successfully.")
            else:
                print("'announcements' table already exists.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    patch_db()
