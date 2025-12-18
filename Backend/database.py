# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pymysql

# 這是雲端必備的 (解決密碼加密問題)
pymysql.install_as_MySQLdb()

# ==========================================
# 【請填入你在 Aiven 看到的真實資料】
# 格式: mysql+pymysql://帳號:密碼@主機網址:Port/defaultdb
# 注意 1: 網址前面要加 mysql+pymysql
# 注意 2: Port 不要寫 3306，要寫 Aiven 給你的那個五位數
# ==========================================

# 範例 (請把下面的資料換成你的)：
USER = "avnadmin"
PASSWORD = "AVNS_wpMgWFawTeSbnCOGuxo"
HOST = "gfmotor-gfmotor001.j.aivencloud.com" # 這裡不能打錯
PORT = "12676" # Aiven 給你的 Port
DB_NAME = "gfmotor" # Aiven 預設是 defaultdb，除非你自己建了 gf_motor

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

# 如果你需要更強制的 SSL 設定，可以用下面這行 (通常上面那行就夠了)
# SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}?ssl_ca=ca.pem"


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()