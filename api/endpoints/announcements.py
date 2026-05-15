from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import asc
from typing import List, Optional
import os
import cloudinary
import cloudinary.uploader

from db.database import get_db
from db import models
from schemas import announcement as ann_schema

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

router = APIRouter()

# ========== 公開 API（首頁用）==========

@router.get("/", response_model=List[ann_schema.Announcement], summary="取得所有啟用中的公告")
def get_active_announcements(db: Session = Depends(get_db)):
    """取得所有 is_active=1 的公告，依 sort_order 排序。"""
    return db.query(models.Announcement).filter(
        models.Announcement.is_active == 1
    ).order_by(asc(models.Announcement.sort_order)).all()


@router.get("/all", response_model=List[ann_schema.Announcement], summary="取得所有公告（含停用）")
def get_all_announcements(db: Session = Depends(get_db)):
    """管理員用，取得全部公告。"""
    return db.query(models.Announcement).order_by(asc(models.Announcement.sort_order)).all()


# ========== 管理（上傳 / 更新 / 刪除）==========

@router.post("/", response_model=ann_schema.Announcement, summary="上傳新公告")
def create_announcement(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    sort_order: int = Form(0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        result = cloudinary.uploader.upload(file.file, folder="gfmotor/announcements")
        image_url = result.get("secure_url")
        public_id = result.get("public_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"圖片上傳失敗: {str(e)}")

    announcement = models.Announcement(
        title=title,
        description=description,
        image_url=image_url,
        cloudinary_public_id=public_id,
        sort_order=sort_order
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.put("/{announcement_id}", response_model=ann_schema.Announcement, summary="更新公告")
def update_announcement(
    announcement_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    ann = db.query(models.Announcement).get(announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="找不到該公告")

    if title is not None:
        ann.title = title
    if description is not None:
        ann.description = description
    if sort_order is not None:
        ann.sort_order = sort_order

    # 如果有上傳新圖片，先刪除舊的再上傳新的
    if file and file.filename:
        try:
            if ann.cloudinary_public_id:
                cloudinary.uploader.destroy(ann.cloudinary_public_id)
            result = cloudinary.uploader.upload(file.file, folder="gfmotor/announcements")
            ann.image_url = result.get("secure_url")
            ann.cloudinary_public_id = result.get("public_id")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片更新失敗: {str(e)}")

    db.commit()
    db.refresh(ann)
    return ann


@router.delete("/{announcement_id}", summary="刪除公告")
def delete_announcement(announcement_id: int, db: Session = Depends(get_db)):
    ann = db.query(models.Announcement).get(announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="找不到該公告")

    # 從 Cloudinary 刪除圖片
    if ann.cloudinary_public_id:
        try:
            cloudinary.uploader.destroy(ann.cloudinary_public_id)
        except Exception:
            pass  # 即使 Cloudinary 刪除失敗，仍然繼續刪除資料庫記錄

    db.delete(ann)
    db.commit()
    return {"detail": "公告已刪除"}
