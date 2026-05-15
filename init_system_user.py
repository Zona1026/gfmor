import sys
sys.path.append("d:/Python/GFmoter")
from db.database import SessionLocal
from db import models

def init():
    db = SessionLocal()
    try:
        sys_user = db.query(models.User).filter(models.User.google_id == "system").first()
        if not sys_user:
            print("Creating system user...")
            sys_user = models.User(
                google_id="system",
                name="System",
                email="system@gfmoter.tw",
                category=models.UserCategory.ADMIN
            )
            db.add(sys_user)
            db.commit()
            db.refresh(sys_user)
        else:
            print("System user already exists.")

        sys_motor = db.query(models.Motor).filter(models.Motor.google_id == "system").first()
        if not sys_motor:
            print("Creating system motor...")
            sys_motor = models.Motor(
                google_id="system",
                license_plate="SYS-0000",
                brand="System",
                model_name="N/A",
                vin="SYS0000000"
            )
            db.add(sys_motor)
            db.commit()
        else:
            print("System motor already exists.")
            
    finally:
        db.close()

if __name__ == "__main__":
    init()
