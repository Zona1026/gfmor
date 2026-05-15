from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from db import models
from schemas import admin as admin_schema
from db.database import get_db
from core.security import get_password_hash # Reuse the hashing function

router = APIRouter()

@router.get("/", response_model=List[admin_schema.AdminDetail])
def get_admins(db: Session = Depends(get_db)):
    """
    列出所有管理員帳號
    """
    return db.query(models.Admin).all()

@router.post("/", response_model=admin_schema.AdminDetail, summary="新增管理員")
def create_admin(admin_in: admin_schema.AdminCreate, db: Session = Depends(get_db)):
    """
    建立新的後台管理員
    """
    # 檢查帳號是否已存在
    db_admin = db.query(models.Admin).filter(models.Admin.username == admin_in.username).first()
    if db_admin:
        raise HTTPException(status_code=400, detail="此帳號已存在")
    
    new_admin = models.Admin(
        username=admin_in.username,
        full_name=admin_in.full_name,
        hashed_password=get_password_hash(admin_in.password)
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

@router.put("/{admin_id}", response_model=admin_schema.AdminDetail, summary="更新管理員資料")
def update_admin(admin_id: int, admin_in: admin_schema.AdminUpdate, db: Session = Depends(get_db)):
    """
    更新管理員帳號、姓名或密碼
    """
    db_admin = db.query(models.Admin).get(admin_id)
    if not db_admin:
        raise HTTPException(status_code=404, detail="找不到該管理員")
    
    if admin_in.username and admin_in.username != db_admin.username:
        # 檢查新帳號是否衝突
        conflict = db.query(models.Admin).filter(models.Admin.username == admin_in.username).first()
        if conflict:
            raise HTTPException(status_code=400, detail="此帳號已存在")
        db_admin.username = admin_in.username
    
    if admin_in.full_name is not None:
        db_admin.full_name = admin_in.full_name
        
    if admin_in.password:
        db_admin.hashed_password = get_password_hash(admin_in.password)
        
    db.commit()
    db.refresh(db_admin)
    return db_admin

@router.delete("/{admin_id}")
def delete_admin(admin_id: int, db: Session = Depends(get_db)):
    """
    刪除管理員帳號
    """
    admin = db.query(models.Admin).filter(models.Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="找不到該管理員")
    
    # 防止刪除最後一個管理員（簡單保護）
    admin_count = db.query(models.Admin).count()
    if admin_count <= 1:
        raise HTTPException(status_code=400, detail="無法刪除唯一的管理員帳號")

    db.delete(admin)
    db.commit()
    return {"message": "管理員帳號已刪除"}
