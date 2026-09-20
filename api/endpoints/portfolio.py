from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pathlib import Path
from uuid import uuid4
import shutil
import cloudinary
import cloudinary.uploader

from core.config import settings
from db.database import get_db
from db import models
from schemas import portfolio as port_schema
from api.dependencies.admin_auth import require_super_admin

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)

router = APIRouter()

LOCAL_PUBLIC_ID_PREFIX = "local:"
IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


def _upload_portfolio_image(file: UploadFile, request: Request):
    storage = settings.PORTFOLIO_STORAGE.lower()
    if storage == "local":
        extension = IMAGE_EXTENSIONS.get(file.content_type or "")
        if not extension:
            raise ValueError("僅支援 JPG、PNG、WebP、GIF 或 AVIF 圖片")

        upload_dir = Path(settings.PORTFOLIO_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}{extension}"
        target = upload_dir / filename
        with target.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        image_url = str(request.url_for("portfolio_uploads", path=filename))
        return image_url, f"{LOCAL_PUBLIC_ID_PREFIX}{filename}"

    if storage != "cloudinary":
        raise RuntimeError(f"不支援的作品集圖片儲存方式: {settings.PORTFOLIO_STORAGE}")
    if not all(
        (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    ):
        raise RuntimeError("Cloudinary 圖片服務尚未設定")

    result = cloudinary.uploader.upload(file.file, folder="gfmotor/portfolio")
    return result.get("secure_url"), result.get("public_id")


def _delete_portfolio_image(public_id: Optional[str]):
    if not public_id:
        return
    if public_id.startswith(LOCAL_PUBLIC_ID_PREFIX):
        filename = Path(public_id.removeprefix(LOCAL_PUBLIC_ID_PREFIX)).name
        (Path(settings.PORTFOLIO_UPLOAD_DIR) / filename).unlink(missing_ok=True)
        return
    cloudinary.uploader.destroy(public_id)

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
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    try:
        image_url, public_id = _upload_portfolio_image(file, request)
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
    request: Request,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_super_admin),
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
            image_url, public_id = _upload_portfolio_image(file, request)
            _delete_portfolio_image(item.cloudinary_public_id)
            item.image_url = image_url
            item.cloudinary_public_id = public_id
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片更新失敗: {str(e)}")

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", summary="刪除作品")
def delete_portfolio_item(
    item_id: int,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    item = db.query(models.PortfolioItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到該作品")

    if item.cloudinary_public_id:
        try:
            _delete_portfolio_image(item.cloudinary_public_id)
        except Exception:
            pass

    db.delete(item)
    db.commit()
    return {"detail": "作品已刪除"}
