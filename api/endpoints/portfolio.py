from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import os
import cloudinary
import cloudinary.uploader

from db.database import get_db
from db import models
from schemas import portfolio as port_schema

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

router = APIRouter()

# ========== 公開 API（消費者端）==========

@router.get("/", response_model=List[port_schema.Portfolio], summary="取得所有作品")
def get_all_portfolio(db: Session = Depends(get_db)):
    return db.query(models.PortfolioItem).order_by(desc(models.PortfolioItem.created_at)).all()


@router.get("/category/{category}", response_model=List[port_schema.Portfolio], summary="依分類取得作品")
def get_portfolio_by_category(category: str, db: Session = Depends(get_db)):
    return db.query(models.PortfolioItem).filter(
        models.PortfolioItem.category == category
    ).order_by(desc(models.PortfolioItem.created_at)).all()


@router.get("/{item_id}", response_model=port_schema.Portfolio, summary="取得單一作品詳情")
def get_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PortfolioItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該作品")
    return item


# ========== 管理端（上傳 / 更新 / 刪除）==========

@router.post("/", response_model=port_schema.Portfolio, summary="上傳新作品")
def create_portfolio_item(
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        result = cloudinary.uploader.upload(file.file, folder="gfmotor/portfolio")
        image_url = result.get("secure_url")
        public_id = result.get("public_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"圖片上傳失敗: {str(e)}")

    item = models.PortfolioItem(
        title=title,
        category=category,
        description=description,
        image_url=image_url,
        cloudinary_public_id=public_id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=port_schema.Portfolio, summary="更新作品")
def update_portfolio_item(
    item_id: int,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    item = db.query(models.PortfolioItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該作品")

    if title is not None:
        item.title = title
    if category is not None:
        item.category = category
    if description is not None:
        item.description = description

    # 如果有上傳新圖片
    if file and file.filename:
        try:
            if item.cloudinary_public_id:
                cloudinary.uploader.destroy(item.cloudinary_public_id)
            result = cloudinary.uploader.upload(file.file, folder="gfmotor/portfolio")
            item.image_url = result.get("secure_url")
            item.cloudinary_public_id = result.get("public_id")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片更新失敗: {str(e)}")

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", summary="刪除作品")
def delete_portfolio_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.PortfolioItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該作品")

    if item.cloudinary_public_id:
        try:
            cloudinary.uploader.destroy(item.cloudinary_public_id)
        except Exception:
            pass

    db.delete(item)
    db.commit()
    return {"detail": "作品已刪除"}
