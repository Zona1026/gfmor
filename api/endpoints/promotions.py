from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from api.dependencies.admin_auth import require_admin, require_manager_admin
from db.database import get_db
from db.models import Product, Promotion
from db import promotions as promotion_service
from schemas.promotion import PromotionInput, PromotionPreview

router = APIRouter()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def status_of(activity, now):
    if activity.ended_at or activity.ends_at <= now:
        return 'ENDED'
    if not activity.is_active:
        return 'DISABLED'
    return 'SCHEDULED' if activity.starts_at > now else 'CURRENT'


def serialize(activity, now):
    return {
        'id': activity.id, 'name': activity.name, 'description': activity.description,
        'starts_at': activity.starts_at.isoformat() + 'Z',
        'ends_at': activity.ends_at.isoformat() + 'Z',
        'discount_type': activity.discount_type, 'discount_value': activity.discount_value,
        'is_active': activity.is_active, 'status': status_of(activity, now),
        'product_ids': [product.id for product in activity.products],
        'products': [{'id': product.id, 'name': product.name} for product in activity.products],
        'buy_quantity': activity.buy_quantity, 'gift_quantity': activity.gift_quantity,
        'gift_product_id': activity.gift_product_id,
        'gift_product': {'id': activity.gift_product.id, 'name': activity.gift_product.name} if activity.gift_product else None,
        'allow_discount_stacking': activity.allow_discount_stacking,
    }


def find_activity(db, activity_id):
    activity = db.get(Promotion, activity_id)
    if activity is None:
        raise HTTPException(404, '找不到活動')
    return activity


def save_settings(db, activity, payload):
    if payload.gift_product_id and db.get(Product, payload.gift_product_id) is None:
        raise HTTPException(400, '贈品不存在，請重新選擇')
    products = db.query(Product).filter(Product.id.in_(payload.product_ids)).all()
    if len(products) != len(payload.product_ids):
        raise HTTPException(400, '部分商品不存在，請重新選擇')
    for key, value in payload.model_dump(exclude={'product_ids'}).items():
        setattr(activity, key, value)
    activity.products = products
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return serialize(activity, utcnow())


@router.get('/')
def list_activities(admin=Depends(require_admin), db: Session = Depends(get_db)):
    now = utcnow()
    activities = db.query(Promotion).options(selectinload(Promotion.products)).order_by(Promotion.starts_at.desc(), Promotion.id.desc()).all()
    return [serialize(activity, now) for activity in activities]


@router.post('/')
def create_activity(payload: PromotionInput, admin=Depends(require_manager_admin), db: Session = Depends(get_db)):
    if payload.ends_at <= utcnow():
        raise HTTPException(400, '新活動的結束時間必須在未來')
    return save_settings(db, Promotion(), payload)


@router.put('/{activity_id}')
def update_activity(activity_id: int, payload: PromotionInput, admin=Depends(require_manager_admin), db: Session = Depends(get_db)):
    activity = find_activity(db, activity_id)
    if status_of(activity, utcnow()) == 'ENDED':
        raise HTTPException(409, '已結束活動不可修改，請建立新活動')
    return save_settings(db, activity, payload)


@router.post('/{activity_id}/end')
def end_activity(activity_id: int, admin=Depends(require_manager_admin), db: Session = Depends(get_db)):
    activity = find_activity(db, activity_id)
    if not activity.ended_at:
        activity.ended_at = utcnow()
        activity.is_active = False
        db.commit()
    return serialize(activity, utcnow())


@router.get('/quote/{product_id}')
def quote_product(product_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, '找不到商品')
    return promotion_service.product_quote(product, promotion_service.current_activities(db, utcnow()))


@router.post('/preview')
def preview_order(payload: PromotionPreview, admin=Depends(require_admin), db: Session = Depends(get_db)):
    activities = promotion_service.current_activities(db, utcnow())
    lines = [line.model_dump() for line in payload.line_items]
    gifts, no_discount = promotion_service.gift_plan(activities, lines)
    product_ids = {line.product_id for line in payload.line_items if line.product_id and not line.promotion_gift_id and line.type == 'PART'}
    products = db.query(Product).filter(Product.id.in_(product_ids)).all()
    return {'gifts': gifts, 'prices': [promotion_service.product_quote(product, activities, product.id in no_discount) for product in products]}
