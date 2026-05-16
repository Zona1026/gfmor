import sys
from db.database import SessionLocal
from db.models import SystemSetting

db = SessionLocal()
try:
    settings = db.query(SystemSetting).all()
    for s in settings:
        # print with utf-8 encoding explicitly
        sys.stdout.buffer.write(f"Key: {s.key}, Value: {s.value}\n".encode('utf-8'))
finally:
    db.close()
