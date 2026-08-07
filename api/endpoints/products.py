from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import cloudinary
import cloudinary.uploader

from db import crud, models
from schemas import product as product_schema
from api.dependencies.admin_auth import require_manager_admin
from db.database import get_db

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

router = APIRouter()


def _inventory_type(value: Optional[str]):
    if not value:
        return models.InventoryType.BOTH
    try:
        return models.InventoryType(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="inventory_type must be SHOP, PART, or BOTH")


def _category_payload(category):
    if hasattr(category, "model_dump"):
        return category.model_dump(exclude_unset=True)
    return category.dict(exclude_unset=True)


def _get_category(db: Session, category_id: Optional[int]):
    if not category_id:
        return None
    category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="找不到該商品分類")
    return category


def _sync_product_category(db: Session, product, category_id: Optional[int], category_name: Optional[str] = None):
    category = _get_category(db, category_id)
    if category:
        product.category_id = category.id
        product.category = category.name
        return

    if category_name is not None:
        cleaned_name = category_name.strip()
        if not cleaned_name:
            product.category_id = None
            product.category = None
            return
        existing = db.query(models.ProductCategory).filter(models.ProductCategory.name == cleaned_name).first()
        if not existing:
            existing = models.ProductCategory(name=cleaned_name, sort_order=0, is_active=1)
            db.add(existing)
            db.flush()
        product.category_id = existing.id
        product.category = existing.name


# ========== 公開 API（消費者端）==========

@router.get("/", response_model=List[product_schema.Product], summary="讀取商品列表")
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = crud.get_products(db, skip=skip, limit=limit)
    return products


@router.get("/categories", response_model=List[product_schema.ProductCategory], include_in_schema=False)
@router.get("/categories/", response_model=List[product_schema.ProductCategory], summary="讀取商品分類")
def read_product_categories(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.ProductCategory)
    if active_only:
        query = query.filter(models.ProductCategory.is_active == 1)
    return query.order_by(models.ProductCategory.sort_order.asc(), models.ProductCategory.name.asc()).all()


@router.post("/categories", response_model=product_schema.ProductCategory, include_in_schema=False)
@router.post("/categories/", response_model=product_schema.ProductCategory, summary="新增商品分類")
def create_product_category(
    category: product_schema.ProductCategoryCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    data = _category_payload(category)
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="分類名稱為必填")
    existing = db.query(models.ProductCategory).filter(models.ProductCategory.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="分類名稱已存在")

    db_category = models.ProductCategory(
        name=name,
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", 1),
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.put("/categories/{category_id}", response_model=product_schema.ProductCategory, summary="更新商品分類")
def update_product_category(
    category_id: int,
    category: product_schema.ProductCategoryUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    db_category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="找不到該商品分類")

    data = _category_payload(category)
    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        if not name:
            raise HTTPException(status_code=400, detail="分類名稱為必填")
        duplicate = (
            db.query(models.ProductCategory)
            .filter(models.ProductCategory.name == name, models.ProductCategory.id != category_id)
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="分類名稱已存在")
        db_category.name = name
        for product in db.query(models.Product).filter(models.Product.category_id == category_id).all():
            product.category = name

    if "sort_order" in data and data["sort_order"] is not None:
        db_category.sort_order = data["sort_order"]
    if "is_active" in data and data["is_active"] is not None:
        db_category.is_active = data["is_active"]

    db.commit()
    db.refresh(db_category)
    return db_category


@router.patch("/categories/{category_id}/toggle", response_model=product_schema.ProductCategory, summary="啟用/停用商品分類")
def toggle_product_category(
    category_id: int,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    db_category = db.query(models.ProductCategory).filter(models.ProductCategory.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="找不到該商品分類")
    db_category.is_active = 0 if db_category.is_active else 1
    db.commit()
    db.refresh(db_category)
    return db_category


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
    inventory_type: Optional[str] = Form(None),
    low_stock_threshold: int = Form(5),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    category: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_manager_admin),
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
        inventory_type=_inventory_type(inventory_type),
        low_stock_threshold=low_stock_threshold,
        description=description,
        image_url=image_url,
        cloudinary_public_id=public_id
    )
    _sync_product_category(db, product, category_id=category_id, category_name=category)
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
    inventory_type: Optional[str] = Form(None),
    low_stock_threshold: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    category: Optional[str] = Form(None),
    is_active: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_manager_admin),
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
    if inventory_type is not None:
        product.inventory_type = _inventory_type(inventory_type)
    if low_stock_threshold is not None:
        product.low_stock_threshold = low_stock_threshold
    if description is not None:
        product.description = description
    if category_id is not None or category is not None:
        _sync_product_category(db, product, category_id=category_id, category_name=category)
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
def delete_product(
    product_id: int,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
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
def toggle_product_active(
    product_id: int,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")
    product.is_active = 0 if product.is_active else 1
    db.commit()
    db.refresh(product)
    return product
