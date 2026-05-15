from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# 根據 .env 中的 DATABASE_URL 建立資料庫引擎
# 我們信任 .env 檔案中提供一個完整的、符合 SQLAlchemy 格式的 URL
engine = create_engine(settings.DATABASE_URL)

# 建立一個資料庫 Session 的工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立一個給 ORM Model 繼承用的基底類別
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
