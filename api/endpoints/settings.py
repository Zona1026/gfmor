from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict
from api.dependencies.admin_auth import require_super_admin
from db.database import SessionLocal
from db.models import SystemSetting
from db.points import get_settings_with_point_defaults

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
    return get_settings_with_point_defaults(db)

@router.put("/")
def update_settings(
    settings: Dict[str, Any], 
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    """更新系統設定 (限管理員)"""
    for key, value in settings.items():
        if isinstance(value, bool):
            stored_value = "true" if value else "false"
        else:
            stored_value = "" if value is None else str(value)

        db_setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if db_setting:
            db_setting.value = stored_value
        else:
            # 如果不存在，可以選擇是否自動建立
            new_setting = SystemSetting(key=key, value=stored_value)
            db.add(new_setting)
    db.commit()
    return {"message": "設定已更新"}
