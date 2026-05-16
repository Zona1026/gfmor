from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from db.database import SessionLocal
from db.models import SystemSetting
from .auth import get_current_admin

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    """取得所有系統設定 (公開)"""
    settings = db.query(SystemSetting).all()
    return {s.key: s.value for s in settings}

@router.put("/")
def update_settings(
    settings: Dict[str, str], 
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """更新系統設定 (限管理員)"""
    for key, value in settings.items():
        db_setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if db_setting:
            db_setting.value = value
        else:
            # 如果不存在，可以選擇是否自動建立
            new_setting = SystemSetting(key=key, value=value)
            db.add(new_setting)
    db.commit()
    return {"message": "設定已更新"}
