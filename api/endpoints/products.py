from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from typing import List, Optional
import json
import os
import cloudinary
import cloudinary.uploader

from db import crud, models
from schemas import product as product_schema
from api.dependencies.admin_auth import require_manager_admin, require_admin, require_super_admin
from db.database import get_db

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

router = APIRouter()


def _parse_product_details(metadata_json, supplier_prices_json):
    details = {}
    try:
        if metadata_json is not None:
            details.update(product_schema.ProductManagementMetadata.model_validate_json(metadata_json).model_dump(exclude_unset=True))
        if supplier_prices_json is not None:
            prices = product_schema.SupplierPrices.model_validate_json(supplier_prices_json)
            details['supplier_prices'] = [price.model_dump(exclude_unset=True) for price in prices.supplier_prices]
    except ValidationError:
        raise HTTPException(status_code=422, detail="商品欄位格式錯誤：金額須為非負整數，進貨廠商名稱不可空白，文字請勿超過長度限制")
    return details


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


def _parse_category_ids(db, raw, category_model=models.ProductCategory):
    if raw is None:
        return None
    try:
        ids = json.loads(raw)
        if not isinstance(ids, list) or any(type(value) is not int or value <= 0 for value in ids):
            raise ValueError()
        ids = list(dict.fromkeys(ids))
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="分類格式錯誤")
    categories = db.query(category_model).filter(category_model.id.in_(ids)).all()
    if len(categories) != len(ids):
        raise HTTPException(status_code=400, detail="找不到該商品分類")
    by_id = {category.id: category for category in categories}
    return [by_id[value] for value in ids]


def _assign_extra_categories(product, categories):
    retained = {category.id for category in product.extra_categories}
    if any(not category.is_active and category.id not in retained for category in categories):
        raise HTTPException(status_code=422, detail="不可選取已停用的其他分類")
    product.extra_categories = categories


def _sync_product_categories(product, categories):
    product.additional_categories = categories
    primary = next((category for category in categories if category.id == product.category_id), None)
    primary = primary or (categories[0] if categories else None)
    product.category_info = primary
    product.category_id = primary.id if primary else None
    product.category = primary.name if primary else None


# ========== 公開 API（消費者端）==========

@router.get("/", response_model=List[product_schema.Product], summary="讀取商品列表")
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = crud.get_products(db, skip=skip, limit=limit)
    return products


@router.get("/paginated", response_model=product_schema.ProductPage, summary="分頁讀取商品列表")
def read_paginated_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    uncategorized: bool = False,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Product).filter(
        models.Product.inventory_type.in_([
            models.InventoryType.SHOP,
            models.InventoryType.BOTH,
        ])
    )

    if search and search.strip():
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Product.name.ilike(keyword),
                models.Product.description.ilike(keyword),
            )
        )

    if uncategorized:
        query = query.filter(models.Product.category_id.is_(None), ~models.Product.additional_categories.any())
    elif category_id is not None:
        query = query.filter(or_(models.Product.category_id == category_id, models.Product.additional_categories.any(models.ProductCategory.id == category_id)))

    if status == "active":
        query = query.filter(models.Product.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(models.Product.is_active.is_(False))
    elif status not in (None, ""):
        raise HTTPException(status_code=422, detail="無效的商品狀態")

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(page, total_pages)
    products = (
        query.order_by(models.Product.id.asc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": products,
        "total": total,
        "page": current_page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


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


@router.get('/admin/', response_model=List[product_schema.AdminProduct], summary='管理端商品與售價列表')
def read_admin_products(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return crud.get_products(db, skip=0, limit=100)


@router.get('/admin/paginated', response_model=product_schema.AdminProductPage, summary='管理端商品分頁與售價')
def read_admin_paginated_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    uncategorized: bool = False,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return read_paginated_products(page, page_size, search, category_id, uncategorized, status, db)


@router.get('/admin/extra-categories', response_model=List[product_schema.ProductExtraCategory])
def read_extra_categories(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.ProductExtraCategory).order_by(models.ProductExtraCategory.sort_order, models.ProductExtraCategory.name).all()


def _save_extra_category(db, category, data):
    for field, value in data.items():
        if value is not None:
            setattr(category, field, value)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="其他分類名稱已存在")
    db.refresh(category)
    return category


@router.post('/admin/extra-categories', response_model=product_schema.ProductExtraCategory)
def create_extra_category(data: product_schema.ProductExtraCategoryCreate, db: Session = Depends(get_db), admin=Depends(require_super_admin)):
    return _save_extra_category(db, models.ProductExtraCategory(), data.model_dump())


@router.put('/admin/extra-categories/{category_id}', response_model=product_schema.ProductExtraCategory)
def update_extra_category(category_id: int, data: product_schema.ProductExtraCategoryUpdate, db: Session = Depends(get_db), admin=Depends(require_super_admin)):
    category = db.get(models.ProductExtraCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="找不到其他分類")
    return _save_extra_category(db, category, data.model_dump(exclude_unset=True))


@router.get('/admin/vehicle-models', response_model=List[str], summary='商品適用車種選單')
def read_product_vehicle_models(db: Session = Depends(get_db), admin=Depends(require_admin)):
    names = {'通用'}
    # Reuse model names only; no customer names, plates or contact data are returned.
    for column in (models.ProductVehicleModel.name, models.Product.vehicle_model,
                   models.Motor.model_name, models.GuestMotor.model_name):
        names.update(row[0].strip() for row in db.query(column).distinct().all()
                     if row[0] and row[0].strip())
    return ['通用', *sorted(names - {'通用'})]


@router.post('/admin/vehicle-models', response_model=str, summary='新增商品適用車種')
def create_product_vehicle_model(
    data: product_schema.ProductVehicleModelCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_manager_admin),
):
    existing = db.query(models.ProductVehicleModel).filter(models.ProductVehicleModel.name == data.name).first()
    if existing:
        return existing.name
    option = models.ProductVehicleModel(name=data.name)
    db.add(option)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(models.ProductVehicleModel).filter(models.ProductVehicleModel.name == data.name).first()
        if existing:
            return existing.name
        raise
    return option.name


@router.get('/admin/{product_id}', response_model=product_schema.AdminProduct, summary='管理端商品與售價詳情')
def read_admin_product(product_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    product = crud.get_product(db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail='找不到該商品')
    return product


@router.get("/{product_id}/supplier-prices", response_model=List[product_schema.SupplierPrice], summary="管理層讀取進貨廠商進價")
def read_product_supplier_prices(
    product_id: int,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    product = crud.get_product(db, product_id=product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="找不到該商品")
    return product.supplier_prices or []


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
    category_ids: Optional[str] = Form(None),
    extra_category_ids: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    product_metadata: Optional[str] = Form(None),
    supplier_prices: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db)
):
    selected_extra_categories = _parse_category_ids(db, extra_category_ids, models.ProductExtraCategory)
    selected_categories = _parse_category_ids(db, category_ids)
    details = _parse_product_details(product_metadata, supplier_prices)
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
    for field, value in details.items():
        setattr(product, field, value)
    _sync_product_category(db, product, category_id=category_id, category_name=category)
    if selected_categories is not None:
        _sync_product_categories(product, selected_categories)
    if selected_extra_categories is not None:
        _assign_extra_categories(product, selected_extra_categories)
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
    category_ids: Optional[str] = Form(None),
    extra_category_ids: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    is_active: Optional[int] = Form(None),
    product_metadata: Optional[str] = Form(None),
    supplier_prices: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="找不到該商品")

    selected_extra_categories = _parse_category_ids(db, extra_category_ids, models.ProductExtraCategory)
    selected_categories = _parse_category_ids(db, category_ids)
    details = _parse_product_details(product_metadata, supplier_prices)
    for field, value in details.items():
        setattr(product, field, value)
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
    if selected_categories is not None:
        _sync_product_categories(product, selected_categories)
    if selected_extra_categories is not None:
        _assign_extra_categories(product, selected_extra_categories)
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
