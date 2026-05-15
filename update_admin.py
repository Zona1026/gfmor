import sys
sys.path.append("d:/Python/GFmoter")
from db.database import SessionLocal
from db.models import Admin
from core.security import get_password_hash

def update_admin():
    db = SessionLocal()
    try:
        old_admin = db.query(Admin).filter(Admin.username == "admin").first()
        if old_admin:
            db.delete(old_admin)
            print("已刪除預設的 admin 帳號。")
            
        new_admin = db.query(Admin).filter(Admin.username == "12345").first()
        if not new_admin:
            hashed_pw = get_password_hash("12345")
            db.add(Admin(username="12345", hashed_password=hashed_pw))
            print("已建立 12345/12345 帳號。")
        else:
            print("12345 帳號已經存在。")
            
        db.commit()
    except Exception as e:
        print("Error:", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_admin()
