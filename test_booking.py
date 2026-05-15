import traceback
import sys
import os

sys.path.append("d:/Python/GFmoter")

from db.database import SessionLocal
from db import crud, models
from schemas.booking import BookingCreate
from datetime import datetime

db = SessionLocal()
user = db.query(models.User).first()
if not user:
    print("No user")
    sys.exit(1)

motor = db.query(models.Motor).filter(models.Motor.google_id == user.google_id).first()
if not motor:
    # 建立一台車
    from schemas.motor import MotorCreate
    motor = models.Motor(google_id=user.google_id, license_plate="TEST-123", brand="YAMAHA", model_name="Cygnus")
    db.add(motor)
    db.commit()
    db.refresh(motor)

booking_data = BookingCreate(
    google_id=user.google_id,
    motor_id=motor.id, # type: ignore
    booking_time=datetime(2026, 3, 27, 14, 0, 0),
    category="保養",
    notes="Test"
)

try:
    print(f"Creating booking for User {user.google_id}, Motor {motor.id}") # type: ignore
    db_booking = crud.create_booking(db, booking_data)
    
    # Simulate FastAPI returning the Pydantic schema
    from schemas.booking import Booking
    print("Validation before returning:")
    booking_out = Booking.from_orm(db_booking)
    print("Success:", booking_out.dict())
except Exception as e:
    traceback.print_exc()
