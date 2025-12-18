# crud.py
from sqlalchemy.orm import Session
import models

# 透過 Google ID 找使用者
def get_user_by_google_id(db: Session, google_id: str):
    return db.query(models.User).filter(models.User.google_id == google_id).first()

# 建立新使用者
def create_google_user(db: Session, user_info: dict):
    # user_info 是我們從 Google token 解析出來的資料
    db_user = models.User(
        google_id=user_info['sub'],  # Google 的唯一 ID (sub)
        email=user_info['email'],
        name=user_info['name'],
        phone=None, # 先留空，讓使用者日後補填
        role="MEMBER"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user