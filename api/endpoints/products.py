from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import cloudinary
import cloudinary.uploader

from db import crud, models
from schemas import product as product_schema
from db.database import get_db

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

router = APIRouter()

# ========== 公開 API（消費者端）==========

@router.get("/", response_model=List[product_schema.Product], summary="讀取商品列表")
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = crud.get_products(db, skip=skip, limit=limit)
    return products


@router.get("/{product_id}", response_model=product_schema.Product, summary="讀取單一商品")
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="找不到該商品")
    return db_product


# ========== 管理端 ==========

@router.post("/", response_model=product_schema.Product, summary="建立新商品（含圖片）")
def create_product_with_image(
    name: str = Form(...),
    price: int = Form(...),
    stock: int = Form(0),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    image_url = None
    public_id = None
    if file and file.filename:
        try:
            result = cloudinary.uploader.upload(file.file, folder="gfmotor/products")
            image_url = result.get("secure_url")
            public_id = result.get("public_id")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片上傳失敗: {str(e)}")

    product = models.Product(
        name=name,
        price=price,
        stock=stock,
        description=description,
        category=category,
        image_url=image_url,
        cloudinary_public_id=public_id
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=product_schema.Product, summary="更新商品（含可選圖片）")
def update_product_with_image(
    product_id: int,
    name: Optional[str] = Form(None),
    price: Optional[int] = Form(None),
    stock: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    is_active: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")

    if name is not None:
        product.name = name
    if price is not None:
        product.price = price
    if stock is not None:
        product.stock = stock
    if description is not None:
        product.description = description
    if category is not None:
        product.category = category
    if is_active is not None:
        product.is_active = is_active

    if file and file.filename:
        try:
            if product.cloudinary_public_id:
                cloudinary.uploader.destroy(product.cloudinary_public_id)
            result = cloudinary.uploader.upload(file.file, folder="gfmotor/products")
            product.image_url = result.get("secure_url")
            product.cloudinary_public_id = result.get("public_id")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"圖片更新失敗: {str(e)}")

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", summary="刪除商品")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")

    if product.cloudinary_public_id:
        try:
            cloudinary.uploader.destroy(product.cloudinary_public_id)
        except Exception:
            pass

    db.delete(product)
    db.commit()
    return {"detail": "商品刪除成功"}


@router.patch("/{product_id}/toggle", response_model=product_schema.Product, summary="上架/下架切換")
def toggle_product_active(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")
    product.is_active = 0 if product.is_active else 1
    db.commit()
    db.refresh(product)
    return product
