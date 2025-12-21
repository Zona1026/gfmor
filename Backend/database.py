# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pymysql

# 這是雲端必備的 (解決密碼加密問題)
pymysql.install_as_MySQLdb()

import os
from dotenv import load_dotenv

# 在本地開發時，從 .env 檔案載入環境變數
load_dotenv()

# ==========================================
#  從環境變數讀取資料庫設定
# ==========================================
USER = os.getenv("DB_USER", "avnadmin")
PASSWORD = os.getenv("DB_PASSWORD", "AVNS_wpMgWFawTeSbnCOGuxo")
HOST = os.getenv("DB_HOST", "gfmotor-gfmotor001.j.aivencloud.com")
PORT = os.getenv("DB_PORT", "12676")
DB_NAME = os.getenv("DB_NAME", "gfmotor")

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