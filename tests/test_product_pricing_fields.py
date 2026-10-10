import asyncio
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from urllib.parse import urlencode, urlsplit
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import products, inventory
from core.config import settings
from db import models
from db.database import Base


class ASGIClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, url, *, data=None, headers=None, json_data=None):
        parsed = urlsplit(url)
        body = json.dumps(json_data).encode() if json_data is not None else urlencode(data or {}).encode()
        content_type = 'application/json' if json_data is not None else 'application/x-www-form-urlencoded'
        messages = []
        scope = {
            'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
            'method': method, 'scheme': 'http', 'path': parsed.path,
            'raw_path': parsed.path.encode(), 'query_string': parsed.query.encode(),
            'root_path': '', 'client': ('127.0.0.1', 1), 'server': ('test', 80),
            'headers': [(key.lower().encode(), value.encode()) for key, value in
                        {'content-type': content_type, **(headers or {})}.items()],
        }

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(scope, receive, send))
        start = next(message for message in messages if message['type'] == 'http.response.start')
        response_body = b''.join(message.get('body', b'') for message in messages if message['type'] == 'http.response.body')
        return SimpleNamespace(status_code=start['status'], data=json.loads(response_body))


class ProductPricingFieldsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        app = FastAPI()
        app.include_router(products.router, prefix='/products')
        app.include_router(inventory.router, prefix='/inventory')
        app.dependency_overrides[products.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def headers(self, role='管理層'):
        token = jwt.encode({'sub': 'pricing-test', 'role': 'admin', 'admin_role': role,
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {'Authorization': f'Bearer {token}'}

    def create(self, **overrides):
        metadata = {'vehicle_model': '勁戰六代', 'specification': '245 mm', 'color': '黑色',
                    'manufacturer': '測試製造廠', 'suggested_price': 1800, 'installation_labor': 350,
                    'wholesale_price': 1200}
        suppliers = [{'supplier_name': f'進貨廠商 {index}', 'purchase_price': 1000 + index} for index in range(6)]
        response = self.client.request('POST', '/products/', headers=self.headers(), data={
            'name': '測試煞車碟盤', 'price': '1500', 'stock': '3', 'inventory_type': 'BOTH',
            'product_metadata': json.dumps(metadata), 'supplier_prices': json.dumps({'supplier_prices': suppliers}),
            **overrides,
        })
        return response

    def test_create_reload_inventory_and_public_prices_without_exposing_costs(self):
        created = self.create()
        self.assertEqual(created.status_code, 200, created.data)
        self.db.expire_all()
        product_id = created.data['id']
        public = self.client.request('GET', f'/products/{product_id}').data
        self.assertEqual(public['vehicle_model'], '勁戰六代')
        self.assertEqual(public['specification'], '245 mm')
        self.assertEqual(public['manufacturer'], '測試製造廠')
        self.assertEqual(public['color'], '黑色')
        self.assertEqual(public['suggested_price'], 1800)
        self.assertEqual(public['installation_labor'], 350)
        self.assertNotIn('supplier_prices', public)
        self.assertNotIn('wholesale_price', public)
        costs = self.client.request('GET', f'/products/{product_id}/supplier-prices', headers=self.headers())
        self.assertEqual(len(costs.data), 6)
        self.assertEqual(costs.data[5]['purchase_price'], 1005)
        for endpoint in ('/products/', '/products/paginated?page=1&page_size=50', '/inventory/items?type=part'):
            response = self.client.request('GET', endpoint, headers=self.headers('一般'))
            self.assertEqual(response.status_code, 200, response.data)
            items = response.data.get('items') if isinstance(response.data, dict) else response.data
            self.assertEqual(items[0]['installation_labor'], 350)
            self.assertNotIn('supplier_prices', items[0])
            if endpoint.startswith('/products'):
                self.assertNotIn('wholesale_price', items[0])
            else:
                self.assertEqual(items[0]['wholesale_price'], 1200)

    def test_wholesale_prices_are_available_to_staff_only_in_admin_routes(self):
        product_id = self.create().data['id']
        for endpoint in ('/products/admin/', '/products/admin/paginated?page=1&page_size=50', f'/products/admin/{product_id}'):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.request('GET', endpoint).status_code, 401)
                response = self.client.request('GET', endpoint, headers=self.headers('一般'))
                self.assertEqual(response.status_code, 200, response.data)
                payload = response.data
                product = payload[0] if isinstance(payload, list) else payload['items'][0] if 'items' in payload else payload
                self.assertEqual(product['price'], 1500)
                self.assertEqual(product['wholesale_price'], 1200)
                self.assertNotIn('supplier_prices', product)

    def test_wholesale_price_edits_leave_retail_and_suppliers_unchanged(self):
        product_id = self.create().data['id']
        for value in (900, 0, None):
            response = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
                'product_metadata': json.dumps({'wholesale_price': value}),
            })
            self.assertEqual(response.status_code, 200, response.data)
            self.db.expire_all()
            product = self.db.get(models.Product, product_id)
            self.assertEqual(product.price, 1500)
            self.assertEqual(product.wholesale_price, value)
            self.assertEqual(len(product.supplier_prices), 6)

    def test_supplier_wholesale_prices_persist_and_hide_costs_from_staff(self):
        suppliers = [
            {'supplier_name': '甲廠商', 'purchase_price': 500, 'wholesale_price': 800},
            {'supplier_name': '乙廠商', 'purchase_price': 550, 'wholesale_price': 900},
            {'supplier_name': '零元廠商', 'purchase_price': 0, 'wholesale_price': 0},
            {'supplier_name': '未設定廠商', 'purchase_price': 600},
        ]
        created = self.create(supplier_prices=json.dumps({'supplier_prices': suppliers}))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        costs = self.client.request('GET', f'/products/{product_id}/supplier-prices', headers=self.headers()).data
        self.assertEqual([row['wholesale_price'] for row in costs], [800, 900, 0, None])
        for endpoint in ('/products/admin/', '/products/admin/paginated', f'/products/admin/{product_id}', '/inventory/items'):
            response = self.client.request('GET', endpoint, headers=self.headers('一般'))
            self.assertEqual(response.status_code, 200, response.data)
            payload = response.data
            product = payload[0] if isinstance(payload, list) else payload['items'][0] if 'items' in payload else payload
            rows = product['supplier_wholesale_prices']
            self.assertEqual([row['wholesale_price'] for row in rows], [800, 900, 0, None])
            self.assertTrue(all(set(row) == {'supplier_name', 'wholesale_price'} for row in rows))
        public = self.client.request('GET', f'/products/{product_id}').data
        self.assertNotIn('supplier_wholesale_prices', public)
        suppliers[0]['wholesale_price'] = None
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
            'supplier_prices': json.dumps({'supplier_prices': suppliers}),
        })
        self.assertEqual(updated.status_code, 200, updated.data)
        self.db.expire_all()
        product = self.db.get(models.Product, product_id)
        self.assertIsNone(product.supplier_prices[0]['wholesale_price'])
        self.assertEqual(product.supplier_prices[1]['wholesale_price'], 900)
        self.assertEqual(product.price, 1500)
        self.assertEqual(product.wholesale_price, 1200)

    def test_invalid_supplier_wholesale_price_is_rejected(self):
        for value in (-1, 1.5, 'invalid'):
            response = self.create(supplier_prices=json.dumps({'supplier_prices': [
                {'supplier_name': '測試廠商', 'purchase_price': 100, 'wholesale_price': value}
            ]}))
            self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(self.db.query(models.Product).count(), 0)

    def test_multiple_vehicle_models_save_reload_edit_clear_and_legacy(self):
        created = self.create(product_metadata=json.dumps({'vehicle_models': [' 勁戰六代 ', 'JET SL', 'JET SL']}))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        for endpoint in (f'/products/{product_id}', '/inventory/items?type=part'):
            response = self.client.request('GET', endpoint, headers=self.headers())
            self.assertEqual(response.status_code, 200, response.data)
            payload = response.data[0] if isinstance(response.data, list) else response.data
            self.assertEqual(payload['vehicle_models'], ['勁戰六代', 'JET SL'])
        options = self.client.request('GET', '/products/admin/vehicle-models', headers=self.headers()).data
        self.assertIn('JET SL', options)
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'name': '改名'})
        self.assertEqual(updated.data['vehicle_models'], ['勁戰六代', 'JET SL'])
        legacy = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
            'product_metadata': json.dumps({'vehicle_model': '舊版單選'}),
        })
        self.assertEqual(legacy.data['vehicle_models'], ['舊版單選'])
        cleared = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
            'product_metadata': json.dumps({'vehicle_models': []}),
        })
        self.assertEqual(cleared.data['vehicle_models'], [])
        self.assertIsNone(cleared.data['vehicle_model'])
        old = models.Product(name='既有零件', price=100, stock=0, vehicle_model='既有車種')
        self.db.add(old)
        self.db.commit()
        self.assertEqual(self.client.request('GET', f'/products/{old.id}').data['vehicle_models'], ['既有車種'])
        for value in ([''], ['x' * 201], 'JET SL', [3]):
            invalid = self.create(product_metadata=json.dumps({'vehicle_models': value}))
            self.assertEqual(invalid.status_code, 422, invalid.data)

    def test_vehicle_models_migration_preserves_existing_single_model(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261010_0026_product_vehicle_models.py'
        spec = importlib.util.spec_from_file_location('vehicle_models_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO products (name, price, stock, vehicle_model) VALUES ('既有', 100, 2, 'JET SL')"))
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT vehicle_model, vehicle_models FROM products')).one(), ('JET SL', None))

    def test_model_number_persists_separately_and_can_be_cleared(self):
        created = self.create(product_metadata=json.dumps({'model_number': 'ABC-123', 'specification': '245 mm'}))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        for endpoint in (f'/products/{product_id}', f'/products/admin/{product_id}', '/inventory/items'):
            response = self.client.request('GET', endpoint, headers=self.headers())
            self.assertEqual(response.status_code, 200, response.data)
            product = response.data[0] if isinstance(response.data, list) else response.data
            self.assertEqual(product['model_number'], 'ABC-123')
            self.assertEqual(product['specification'], '245 mm')
        response = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'name': '新名稱'})
        self.assertEqual(response.data['model_number'], 'ABC-123')
        response = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
            'product_metadata': json.dumps({'model_number': None}),
        })
        self.assertIsNone(response.data['model_number'])
        self.assertEqual(response.data['specification'], '245 mm')
        invalid = self.create(product_metadata=json.dumps({'model_number': 'x' * 201}))
        self.assertEqual(invalid.status_code, 422)

    def test_model_number_migration_preserves_existing_products(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261009_0020_product_model_number.py'
        spec = importlib.util.spec_from_file_location('model_number_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            connection.execute(text('INSERT INTO products (name, price, stock, specification) VALUES (:name, 100, 2, :spec)'),
                               {'name': '既有商品', 'spec': '舊規格'})
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                migration.upgrade()
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT price, specification, model_number FROM products')).one(),
                             (100, '舊規格', None))

    def test_multiple_categories_save_filter_and_clear(self):
        normal = models.ProductCategory(name='機油', is_active=1)
        promotion = models.ProductCategory(name='活動特價', is_active=1)
        self.db.add_all([normal, promotion])
        self.db.commit()
        ids = [normal.id, promotion.id]
        created = self.create(category_id=str(normal.id), category_ids=json.dumps(ids + [promotion.id]))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        self.assertEqual({category['id'] for category in created.data['categories']}, set(ids))
        for category_id in ids:
            response = self.client.request('GET', f'/products/paginated?category_id={category_id}')
            self.assertEqual(response.data['total'], 1)
            self.assertEqual(response.data['items'][0]['id'], product_id)
        response = self.client.request('GET', '/products/paginated?uncategorized=true')
        self.assertEqual(response.data['total'], 0)
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'name': '改名'})
        self.assertEqual(len(updated.data['categories']), 2)
        inventory_data = self.client.request('GET', '/inventory/items', headers=self.headers('一般')).data[0]
        self.assertEqual({category['id'] for category in inventory_data['categories']}, set(ids))
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={
            'category_ids': json.dumps([promotion.id]),
        })
        self.assertEqual(updated.data['category_id'], promotion.id)
        self.assertEqual([category['name'] for category in updated.data['categories']], ['活動特價'])
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'category_ids': '[]'})
        self.assertIsNone(updated.data['category_id'])
        self.assertEqual(updated.data['categories'], [])
        self.assertEqual(self.client.request('GET', '/products/paginated?uncategorized=true').data['total'], 1)

    def test_multiple_category_validation_and_legacy_compatibility(self):
        category = models.ProductCategory(name='旧分類', is_active=1)
        self.db.add(category)
        self.db.commit()
        created = self.create(category_id=str(category.id))
        self.assertEqual(created.data['categories'][0]['id'], category.id)
        self.assertEqual(self.client.request('GET', f'/products/paginated?category_id={category.id}').data['total'], 1)
        for raw, status in [('bad', 422), ('{}', 422), ('[true]', 422), ('[0]', 422), ('[999999]', 400)]:
            response = self.create(category_ids=raw)
            self.assertEqual(response.status_code, status, response.data)
        self.assertEqual(self.db.query(models.Product).count(), 1)

    def test_multiple_category_migration_is_repeatable_and_preserves_primary(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261009_0021_product_categories.py'
        spec = importlib.util.spec_from_file_location('product_categories_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        category = models.ProductCategory(name='原分類')
        self.db.add(category)
        self.db.commit()
        product_id = self.create(category_id=str(category.id)).data['id']
        with self.engine.begin() as connection:
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                migration.upgrade()
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT category_id FROM products WHERE id = :id'), {'id': product_id}).scalar(), category.id)

    def test_product_barcode_preserves_leading_zero_and_can_clear(self):
        created = self.create(product_metadata=json.dumps({'barcode': ' 0012345678905 '}))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        self.assertEqual(self.db.get(models.Product, product_id).barcode, '0012345678905')
        for endpoint in (f'/products/{product_id}', f'/products/admin/{product_id}', '/inventory/items'):
            response = self.client.request('GET', endpoint, headers=self.headers())
            payload = response.data[0] if isinstance(response.data, list) else response.data
            self.assertEqual(payload['barcode'], '0012345678905')
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'name': '新名稱'})
        self.assertEqual(updated.data['barcode'], '0012345678905')
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'product_metadata': json.dumps({'barcode': None})})
        self.assertIsNone(updated.data['barcode'])
        for value in ('含中文', 'ABC DEF', 'A\nB', 'x' * 101):
            response = self.create(product_metadata=json.dumps({'barcode': value}))
            self.assertEqual(response.status_code, 422, response.data)

    def test_extra_category_catalog_requires_super_for_definition(self):
        endpoint = '/products/admin/extra-categories'
        for role in ('一般', '管理層'):
            response = self.client.request('POST', endpoint, headers=self.headers(role), json_data={'name': '活動特價'})
            self.assertEqual(response.status_code, 403)
        created = self.client.request('POST', endpoint, headers=self.headers('最高級'), json_data={'name': ' 活動特價 '})
        self.assertEqual(created.status_code, 200, created.data)
        category_id = created.data['id']
        self.assertEqual(created.data['name'], '活動特價')
        self.assertEqual(self.db.query(models.ProductCategory).count(), 0)
        for role in ('一般', '管理層'):
            self.assertEqual(self.client.request('GET', endpoint, headers=self.headers(role)).status_code, 200)
            response = self.client.request('PUT', f'{endpoint}/{category_id}', headers=self.headers(role), json_data={'name': '改名'})
            self.assertEqual(response.status_code, 403)
        updated = self.client.request('PUT', f'{endpoint}/{category_id}', headers=self.headers('最高級'), json_data={'name': '限定活動', 'is_active': 0})
        self.assertEqual(updated.data['name'], '限定活動')
        self.assertEqual(updated.data['is_active'], 0)
        self.assertEqual(self.client.request('GET', endpoint).status_code, 401)
        for name in (' ', 'x' * 101):
            response = self.client.request('POST', endpoint, headers=self.headers('最高級'), json_data={'name': name})
            self.assertEqual(response.status_code, 422)
        duplicate = self.client.request('POST', endpoint, headers=self.headers('最高級'), json_data={'name': '限定活動'})
        self.assertEqual(duplicate.status_code, 400)

    def test_independent_extra_categories_save_reload_and_retain_inactive_values(self):
        main = models.ProductCategory(name='機油')
        extra = models.ProductExtraCategory(name='活動特價')
        self.db.add_all([main, extra]); self.db.commit()
        created = self.create(category_id=str(main.id), extra_category_ids=json.dumps([extra.id, extra.id]))
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data['id']
        self.db.expire_all()
        self.assertEqual([category['name'] for category in created.data['categories']], ['機油'])
        self.assertEqual([category['name'] for category in created.data['extra_categories']], ['活動特價'])
        # IDs may overlap because the two catalogs are independent.
        extra.name = '限時特價'; extra.is_active = 0; self.db.commit()
        updated = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'extra_category_ids': json.dumps([extra.id])})
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data['extra_categories'][0]['name'], '限時特價')
        self.assertEqual(updated.data['category'], '機油')
        self.assertEqual(self.client.request('GET', '/inventory/items', headers=self.headers('一般')).data[0]['extra_categories'][0]['is_active'], 0)
        # Disabled definitions cannot be assigned to a new product.
        invalid = self.create(extra_category_ids=json.dumps([extra.id]))
        self.assertEqual(invalid.status_code, 422)
        cleared = self.client.request('PUT', f'/products/{product_id}', headers=self.headers(), data={'extra_category_ids': '[]'})
        self.assertEqual(cleared.data['extra_categories'], [])
        self.assertEqual(cleared.data['category'], '機油')

    def test_barcode_extra_category_migration_moves_only_secondary_links(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261009_0022_product_barcode_extra_categories.py'
        spec = importlib.util.spec_from_file_location('barcode_extra_migration', path)
        migration = importlib.util.module_from_spec(spec); spec.loader.exec_module(migration)
        main = models.ProductCategory(name='機油', sort_order=0, is_active=1)
        secondary = models.ProductCategory(name='活動特價', sort_order=2, is_active=1)
        self.db.add_all([main, secondary]); self.db.commit()
        product_id = self.create(category_id=str(main.id), category_ids=json.dumps([main.id, secondary.id])).data['id']
        with self.engine.begin() as connection:
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade(); migration.upgrade(); migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT price, category_id, barcode FROM products WHERE id = :id'), {'id': product_id}).one(), (1500, main.id, None))
            self.assertEqual(connection.execute(text('SELECT name FROM product_extra_categories')).scalar(), '活動特價')
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM product_extra_category_links')).scalar(), 1)
            self.assertEqual(connection.execute(text('SELECT category_id FROM product_category_links')).scalar(), main.id)
            self.assertEqual(connection.execute(text('SELECT COUNT(*) FROM product_categories')).scalar(), 2)

    def test_supplier_prices_require_manager_authentication(self):
        product_id = self.create().data['id']
        endpoint = f'/products/{product_id}/supplier-prices'
        self.assertEqual(self.client.request('GET', endpoint).status_code, 401)
        self.assertEqual(self.client.request('GET', endpoint, headers=self.headers('一般')).status_code, 403)
        self.assertEqual(self.client.request('GET', endpoint, headers=self.headers('最高級')).status_code, 200)

    def test_vehicle_options_collect_existing_models_without_customer_data(self):
        self.create()
        self.db.add_all([
            models.Motor(google_id='private-owner', license_plate='PRIVATE-001', model_name=' JET SL '),
            models.Motor(google_id='private-owner', license_plate='PRIVATE-002', model_name='JET SL'),
            models.GuestMotor(guest_customer_id=1, license_plate='PRIVATE-003', model_name='勁戰六代'),
            models.GuestMotor(guest_customer_id=1, license_plate='PRIVATE-004', model_name='  '),
            models.ProductVehicleModel(name='測試車種'),
        ])
        self.db.commit()
        response = self.client.request('GET', '/products/admin/vehicle-models', headers=self.headers('一般'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0], '通用')
        self.assertEqual(set(response.data), {'通用', 'JET SL', '勁戰六代', '測試車種'})
        self.assertEqual(response.data.count('JET SL'), 1)
        self.assertNotIn('PRIVATE', json.dumps(response.data))
        self.assertEqual(self.client.request('GET', '/products/admin/vehicle-models').status_code, 401)

    def test_new_vehicle_option_is_persistent_and_duplicates_are_reused(self):
        for name in (' YAMAHA 勁戰七代 ', 'YAMAHA 勁戰七代'):
            response = self.client.request('POST', '/products/admin/vehicle-models', headers=self.headers(), json_data={'name': name})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data, 'YAMAHA 勁戰七代')
        self.db.expire_all()
        self.assertEqual(self.db.query(models.ProductVehicleModel).count(), 1)
        self.assertEqual(self.db.query(models.Product).count(), 0)
        options = self.client.request('GET', '/products/admin/vehicle-models', headers=self.headers()).data
        self.assertIn('YAMAHA 勁戰七代', options)

    def test_vehicle_option_write_validates_name_and_requires_manager(self):
        endpoint = '/products/admin/vehicle-models'
        self.assertEqual(self.client.request('POST', endpoint, json_data={'name': '測試車種'}).status_code, 401)
        self.assertEqual(self.client.request('POST', endpoint, headers=self.headers('一般'), json_data={'name': '測試車種'}).status_code, 403)
        for name in (' ', '', 'x' * 201):
            response = self.client.request('POST', endpoint, headers=self.headers(), json_data={'name': name})
            self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(self.db.query(models.ProductVehicleModel).count(), 0)

    def test_edit_preserves_omitted_fields_and_can_clear_or_set_zero(self):
        product_id = self.create().data['id']
        endpoint = f'/products/{product_id}'
        response = self.client.request('PUT', endpoint, headers=self.headers(), data={'name': '新名稱'})
        self.assertEqual(response.data['installation_labor'], 350)
        self.assertEqual(self.db.get(models.Product, product_id).wholesale_price, 1200)
        self.assertEqual(len(self.db.get(models.Product, product_id).supplier_prices), 6)
        response = self.client.request('PUT', endpoint, headers=self.headers(), data={
            'product_metadata': json.dumps({'vehicle_model': None, 'color': None, 'suggested_price': None, 'installation_labor': 0}),
            'supplier_prices': json.dumps({'supplier_prices': [{'supplier_name': ' 新廠商 ', 'purchase_price': 0}]}),
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['installation_labor'], 0)
        self.assertIsNone(response.data['vehicle_model'])
        self.assertIsNone(response.data['suggested_price'])
        self.assertEqual(self.db.get(models.Product, response.data['id']).wholesale_price, 1200)
        self.assertEqual(self.db.get(models.Product, product_id).supplier_prices, [{'supplier_name': '新廠商', 'purchase_price': 0}])
        response = self.client.request('PUT', endpoint, headers=self.headers(), data={
            'product_metadata': json.dumps({'installation_labor': None}),
            'supplier_prices': '{"supplier_prices": []}',
        })
        self.assertIsNone(response.data['installation_labor'])
        self.assertEqual(self.db.get(models.Product, product_id).supplier_prices, [])

    def test_legacy_client_and_part_only_product_support(self):
        response = self.client.request('POST', '/products/', headers=self.headers(), data={
            'name': '舊格式零件', 'price': '10', 'inventory_type': 'PART',
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['installation_labor'])
        self.assertIsNone(response.data['suggested_price'])
        self.assertEqual(self.db.get(models.Product, response.data['id']).supplier_prices, [])
        self.assertIsNone(self.db.get(models.Product, response.data['id']).wholesale_price)
        self.assertEqual(self.client.request('GET', '/products/paginated?page=1&page_size=50').data['items'], [])

    def test_invalid_details_rejected_before_creating_product(self):
        invalid = [
            {'product_metadata': '{bad'},
            {'product_metadata': '{"installation_labor": -1}'},
            {'product_metadata': '{"suggested_price": 1.5}'},
            {'product_metadata': '{"wholesale_price": -1}'},
            {'product_metadata': '{"wholesale_price": 1.5}'},
            {'supplier_prices': '{"supplier_prices": [{"supplier_name": "   ", "purchase_price": 5}]}'},
            {'supplier_prices': '{"supplier_prices": [{"supplier_name": "廠商", "purchase_price": -1}]}'},
            {'supplier_prices': '[]'},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.create(**payload)
                self.assertEqual(response.status_code, 422, response.data)
        self.assertEqual(self.db.query(models.Product).count(), 0)


class ProductPricingMigrationTest(unittest.TestCase):
    def test_wholesale_migration_preserves_existing_retail_price(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261009_0018_product_wholesale_price.py'
        spec = importlib.util.spec_from_file_location('wholesale_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine('sqlite://')
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE products (id INTEGER PRIMARY KEY, price INTEGER)'))
            connection.execute(text('INSERT INTO products VALUES (1, 1500)'))
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.upgrade()
                migration.upgrade()
                self.assertEqual(connection.execute(text('SELECT price, wholesale_price FROM products')).one(), (1500, None))
                migration.downgrade()
                self.assertEqual(connection.execute(text('SELECT price FROM products')).scalar(), 1500)
        engine.dispose()

    def test_old_product_survives_upgrade_and_downgrade(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261009_0017_product_pricing_fields.py'
        spec = importlib.util.spec_from_file_location('product_pricing_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine('sqlite://')
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(100), price INTEGER, stock INTEGER)'))
            connection.execute(text("INSERT INTO products VALUES (1, '既有商品', 900, 7)"))
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.upgrade()
                row = connection.execute(text('SELECT * FROM products')).mappings().one()
                self.assertEqual(row['price'], 900)
                self.assertEqual(row['stock'], 7)
                self.assertIsNone(row['installation_labor'])
                self.assertEqual(json.loads(row['supplier_prices']), [])
                connection.execute(text("INSERT INTO products (id, name, price, stock) VALUES (2, '舊版本新增', 50, 1)"))
                connection.execute(text('UPDATE products SET supplier_prices = :prices'), {'prices': '[{"supplier_name": "保留", "purchase_price": 99}]'})
                migration.upgrade()  # The baseline may already create these columns.
                self.assertEqual(json.loads(connection.execute(text('SELECT supplier_prices FROM products WHERE id = 1')).scalar())[0]['purchase_price'], 99)
                migration.downgrade()
                self.assertNotIn('installation_labor', {column['name'] for column in inspect(connection).get_columns('products')})
                self.assertEqual(connection.execute(text('SELECT price, stock FROM products WHERE id = 1')).one(), (900, 7))
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
