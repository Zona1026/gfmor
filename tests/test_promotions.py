from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.endpoints import promotions
from db.database import Base
from db.models import Product
from db import crud, inventory, promotions as promotion_service
from schemas.work_order import WorkOrderCreate, WorkOrderUpdate
import test_product_pricing_fields as pricing_tests


class PromotionsTest(unittest.TestCase):
    headers = pricing_tests.ProductPricingFieldsTest.headers

    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([Product(id=1, name='機油', price=105, stock=5), Product(id=2, name='輪胎', price=1000, stock=1)])
        self.db.commit()
        app = FastAPI()
        app.include_router(promotions.router, prefix='/promotions')
        app.dependency_overrides[promotions.get_db] = lambda: self.db
        self.client = pricing_tests.ASGIClient(app)
        self.now = datetime(2026, 10, 10, 10)
        self.clock = patch.object(promotions, 'utcnow', return_value=self.now)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        self.db.close()
        self.engine.dispose()

    def payload(self, **values):
        return {'name': '機油優惠', 'starts_at': (self.now - timedelta(hours=1)).isoformat() + 'Z',
                'ends_at': (self.now + timedelta(hours=1)).isoformat() + 'Z',
                'discount_type': 'PERCENT', 'discount_value': 10, 'product_ids': [1], **values}

    def create(self, **values):
        response = self.client.request('POST', '/promotions/', json_data=self.payload(**values), headers=self.headers())
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def quote(self, product_id=1):
        response = self.client.request('GET', f'/promotions/quote/{product_id}', headers=self.headers('一般'))
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_current_discount_rounding_target_and_best_price(self):
        activity = self.create()
        self.assertEqual(activity['status'], 'CURRENT')
        self.assertEqual(self.quote()['unit_price'], 95)
        self.assertEqual(self.quote(2)['unit_price'], 1000)
        self.create(discount_type='AMOUNT', discount_value=20)
        self.assertEqual(self.quote()['unit_price'], 85)
        self.create(discount_type='AMOUNT', discount_value=200)
        self.assertEqual(self.quote()['unit_price'], 0)

    def test_scheduled_disabled_expired_and_manual_end(self):
        self.create(starts_at=(self.now + timedelta(minutes=1)).isoformat() + 'Z')
        self.create(is_active=False)
        self.assertIsNone(self.quote()['promotion_id'])
        activity = self.create()
        with patch.object(promotions, 'utcnow', return_value=self.now + timedelta(hours=1)):
            self.assertIsNone(self.quote()['promotion_id'])
            listed = self.client.request('GET', '/promotions/', headers=self.headers()).data
            self.assertTrue(all(entry['status'] == 'ENDED' for entry in listed))
        ended = self.client.request('POST', f"/promotions/{activity['id']}/end", headers=self.headers())
        self.assertEqual(ended.data['status'], 'ENDED')
        update = self.client.request('PUT', f"/promotions/{activity['id']}", json_data=self.payload(), headers=self.headers())
        self.assertEqual(update.status_code, 409)
        self.assertIsNone(self.quote()['promotion_id'])

    def test_validation_and_permissions(self):
        for override in [{'name': ' '}, {'discount_value': 101}, {'product_ids': []}, {'starts_at': self.now.isoformat()}, {'ends_at': self.now.isoformat() + 'Z', 'starts_at': self.now.isoformat() + 'Z'}]:
            result = self.client.request('POST', '/promotions/', json_data=self.payload(**override), headers=self.headers())
            self.assertEqual(result.status_code, 422, result.data)
        missing = self.client.request('POST', '/promotions/', json_data=self.payload(product_ids=[99]), headers=self.headers())
        self.assertEqual(missing.status_code, 400)
        forbidden = self.client.request('POST', '/promotions/', json_data=self.payload(), headers=self.headers('一般'))
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(self.client.request('GET', '/promotions/').status_code, 401)
        activity = self.create()
        updated = self.client.request('PUT', f"/promotions/{activity['id']}", json_data=self.payload(discount_type='AMOUNT', discount_value=30, product_ids=[2]), headers=self.headers())
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(self.quote()['unit_price'], 105)
        self.assertEqual(self.quote(2)['unit_price'], 970)

    def preview(self, lines):
        response = self.client.request('POST', '/promotions/preview', json_data={'line_items': lines}, headers=self.headers('一般'))
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_bogo_threshold_sum_gift_exclusion_and_stacking(self):
        self.create(discount_type='BOGO', buy_quantity=3, gift_quantity=2, gift_product_id=2, product_ids=[1, 2])
        self.create()
        self.assertEqual(self.preview([{'product_id': 1, 'quantity': 2}])['gifts'], [])
        result = self.preview([{'product_id': 1, 'quantity': 2}, {'product_id': 2, 'quantity': 1}])
        self.assertEqual(result['gifts'][0]['quantity'], 2)
        self.assertEqual(result['gifts'][0]['unit_price'], 0)
        self.assertEqual(result['prices'][0]['unit_price'], 105)
        gift = result['gifts'][0]
        excluded = self.preview([{'product_id': 1, 'quantity': 2}, gift])
        self.assertEqual(excluded['gifts'], [])
        activity = self.db.get(promotions.Promotion, gift['promotion_gift_id'])
        activity.allow_discount_stacking = True
        self.db.commit()
        self.assertEqual(self.preview([{'product_id': 1, 'quantity': 6}])['gifts'][0]['quantity'], 4)
        self.assertEqual(self.preview([{'product_id': 1, 'quantity': 3}])['prices'][0]['unit_price'], 95)

    def test_bogo_save_reload_zero_price_recompute_and_inventory(self):
        activity = self.create(discount_type='BOGO', buy_quantity=2, gift_quantity=1, gift_product_id=2)
        original = promotion_service.current_activities
        with patch.object(promotion_service, 'current_activities', side_effect=lambda db: original(db, self.now)):
            order = crud.create_work_order(self.db, WorkOrderCreate(vehicle_license_plate='GIFT-TEST', vehicle_model='測試車型', responsible_staff='測試人員', vehicle_mileage=1, line_items=[{'type':'PART', 'name':'機油', 'product_id':1, 'quantity':4, 'unit_price':105}]))
            gifts = [line for line in order.line_items if line.promotion_gift_id]
            self.assertEqual(len(gifts), 1)
            self.assertEqual((gifts[0].quantity, gifts[0].unit_price), (2, 0))
            purchased = [line for line in order.line_items if not line.promotion_gift_id][0]
            order = crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[{'id': purchased.id, 'type':'PART', 'name':'機油', 'product_id':1, 'quantity':2, 'unit_price':105}, {'type':'PART', 'name':'fake gift', 'product_id':2, 'quantity':999, 'unit_price':0, 'promotion_gift_id':activity['id']}]))
            gifts = [line for line in order.line_items if line.promotion_gift_id]
            self.assertEqual(len(gifts), 1)
            self.assertEqual((gifts[0].quantity, gifts[0].unit_price), (1, 0))
            inventory.reserve_work_order_line_item(self.db, gifts[0])
            self.db.flush()
            inventory.consume_work_order_line_item(self.db, gifts[0])
            self.db.commit()
            self.assertEqual(self.db.get(Product, 2).stock, 0)
            self.assertEqual(gifts[0].inventory_consumed_quantity, 1)
            # Consuming again is idempotent.
            inventory.consume_work_order_line_item(self.db, gifts[0])
            self.assertEqual(self.db.get(Product, 2).stock, 0)

    def test_bogo_validation_and_expiry(self):
        for values in [{'gift_product_id': None}, {'gift_product_id': 0}, {'gift_product_id':2, 'buy_quantity':0}, {'gift_product_id':2, 'gift_quantity':0}]:
            response = self.client.request('POST', '/promotions/', json_data=self.payload(discount_type='BOGO', **values), headers=self.headers())
            self.assertEqual(response.status_code, 422)
        missing = self.client.request('POST', '/promotions/', json_data=self.payload(discount_type='BOGO', gift_product_id=99), headers=self.headers())
        self.assertEqual(missing.status_code, 400)
        self.create(discount_type='BOGO', gift_product_id=2, buy_quantity=1)
        with patch.object(promotions, 'utcnow', return_value=self.now + timedelta(hours=2)):
            self.assertEqual(self.preview([{'product_id':1, 'quantity':10}])['gifts'], [])


if __name__ == '__main__':
    unittest.main()
