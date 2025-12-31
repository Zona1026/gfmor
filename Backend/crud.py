# crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from typing import Optional

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

# --- Portfolio CRUD ---

def get_portfolio_item(db: Session, item_id: int):
    return db.query(models.PortfolioItem).filter(models.PortfolioItem.id == item_id).first()

def get_portfolio_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.PortfolioItem).order_by(models.PortfolioItem.created_at.desc()).offset(skip).limit(limit).all()

def create_portfolio_item(db: Session, title: str, description: str, category: str, image_url: str):
    db_item = models.PortfolioItem(
        title=title,
        description=description,
        category=category,
        image_url=image_url
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_portfolio_item(db: Session, item_id: int, title: str, description: str, category: str, image_url: Optional[str] = None):
    db_item = get_portfolio_item(db, item_id)
    if not db_item:
        return None
    
    db_item.title = title
    db_item.description = description
    db_item.category = category
    if image_url:
        db_item.image_url = image_url
        
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_portfolio_item(db: Session, item_id: int):
    db_item = get_portfolio_item(db, item_id)
    if not db_item:
        return None
    
    # Return the image_url so we can delete the file
    image_url = db_item.image_url 
    db.delete(db_item)
    db.commit()
    return image_url

def update_user(db: Session, google_id: str, user_update: schemas.UserUpdateRequest):
    db_user = get_user_by_google_id(db, google_id=google_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user