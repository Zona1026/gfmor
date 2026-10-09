from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import selectinload
from db import models


def current_activities(db, now=None):
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    return db.query(models.Promotion).options(selectinload(models.Promotion.products), selectinload(models.Promotion.gift_product)).filter(
        models.Promotion.is_active.is_(True), models.Promotion.ended_at.is_(None),
        models.Promotion.starts_at <= now, models.Promotion.ends_at > now,
    ).order_by(models.Promotion.id).all()


def gift_plan(activities, lines):
    quantities = {}
    for line in lines:
        if line.get('promotion_gift_id') or line.get('type') != 'PART' or not line.get('product_id') or not line.get('is_confirmed', 1):
            continue
        product_id = line['product_id']
        quantities[product_id] = quantities.get(product_id, 0) + max(0, int(line.get('quantity', 0)))
    gifts, no_discount, allocated = [], set(), set()
    for activity in activities:
        if activity.discount_type != 'BOGO' or not activity.gift_product:
            continue
        product_ids = {product.id for product in activity.products}
        # A purchased unit qualifies for one buy-A-get-B activity, in creation order.
        eligible = product_ids - allocated
        times = sum(quantities.get(product_id, 0) for product_id in eligible) // activity.buy_quantity
        if not times:
            continue
        allocated.update(eligible)
        if not activity.allow_discount_stacking:
            no_discount.update(eligible)
        gifts.append({'promotion_gift_id': activity.id, 'product_id': activity.gift_product_id,
                      'name': f'贈品：{activity.gift_product.name}'[:100], 'quantity': times * activity.gift_quantity,
                      'unit_price': 0, 'type': 'PART', 'is_confirmed': 1,
                      'description': f'買A送B：{activity.name}', 'counts_toward_membership': False, 'points_redeemed': 0})
    return gifts, no_discount


def product_quote(product, activities, no_discount=False):
    original = max(0, int(product.price or 0))
    best_price, best = original, None
    if not no_discount:
        for activity in activities:
            if activity.discount_type == 'BOGO' or product.id not in {value.id for value in activity.products}:
                continue
            value = (Decimal(original) * (100 - activity.discount_value) / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if activity.discount_type == 'PERCENT' else original - activity.discount_value
            price = max(0, int(value))
            if price < best_price:
                best_price, best = price, activity
    return {'product_id': product.id, 'original_price': original, 'unit_price': best_price,
            'promotion_id': best.id if best else None, 'promotion_name': best.name if best else None,
            'bogo_excludes_discount': no_discount}


def sync_gifts(db, order):
    purchased = [line for line in order.line_items if not line.promotion_gift_id]
    lines = [{'type': line.type.value, 'product_id': line.product_id, 'quantity': line.quantity, 'is_confirmed': line.is_confirmed} for line in purchased]
    activities = current_activities(db)
    gifts, no_discount = gift_plan(activities, lines)
    for line in purchased:
        if line.type == models.WorkOrderLineItemType.PART and line.product_id in no_discount:
            # Disallow monetary promotion stacking while preserving explicit manual quotes.
            product = db.get(models.Product, line.product_id)
            quote = product_quote(product, activities)
            if line.unit_price == quote['unit_price'] and quote['promotion_id']:
                line.unit_price = product.price
    for gift in gifts:
        gift['type'] = models.WorkOrderLineItemType.PART
    order.line_items = purchased + [models.WorkOrderLineItem(**gift) for gift in gifts]
