import sys
sys.path.append("d:/Python/GFmoter")
from db.database import engine, SessionLocal
from db.models import Admin, Base
from core.security import get_password_hash

def init_admin():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "admins" in inspector.get_table_names():
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE admins"))
            conn.commit()
        print("Dropped old admins table.")
        
    Admin.__table__.create(engine)
    print("Created admins table.")

    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == "12345").first()
        if not admin:
            print("Creating default admin account...")
            hashed_pw = get_password_hash("12345")
            new_admin = Admin(username="12345", hashed_password=hashed_pw)
            db.add(new_admin)
            db.commit()
            print("Default admin created (12345/12345).")
        else:
            print("Default admin already exists.")
    except Exception as e:
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    init_admin()
