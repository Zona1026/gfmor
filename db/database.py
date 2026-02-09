from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# 根據 .env 中的 DATABASE_URL 建立資料庫引擎
# connect_args 是為了解決 SQLite 在多線程環境下的問題，對於 MySQL 非必需但保留亦無害
engine = create_engine(
    settings.DATABASE_URL, 
    # connect_args={"check_same_thread": False} # 這行僅適用於 SQLite
)

# 建立一個資料庫 Session 的工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立一個給 ORM Model 繼承用的基底類別
Base = declarative_base()
