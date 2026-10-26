from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import products
from core.config import settings
from db import models
from test_product_pricing_fields import ASGIClient


class CategoryManagementTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.categories = [models.ProductCategory(name=name, sort_order=index, is_active=1)
                           for index, name in enumerate(['機油', '輪胎', '空濾'])]
        self.db.add_all(self.categories)
        self.db.commit()
        self.ids = [category.id for category in self.categories]
        app = FastAPI()
        app.include_router(products.router, prefix='/products')
        app.dependency_overrides[products.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def headers(self, role='最高級'):
        token = jwt.encode({'sub': 'category-test', 'role': 'admin', 'admin_role': role,
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {'Authorization': f'Bearer {token}'}

    def reorder(self, ids, role='最高級'):
        return self.client.request('PUT', '/products/categories/reorder', headers=self.headers(role),
                                   json_data={'category_ids': ids})

    def test_all_mutations_require_super_but_staff_can_read(self):
        cases = [('POST', '/products/categories/', {'name': '新增'}),
                 ('PUT', f'/products/categories/{self.ids[0]}', {'name': '改名'}),
                 ('PATCH', f'/products/categories/{self.ids[0]}/toggle', {}),
                 ('PUT', '/products/categories/reorder', {'category_ids': self.ids[::-1]})]
        for role in ['一般', '管理層']:
            for method, url, payload in cases:
                with self.subTest(role=role, url=url):
                    response = self.client.request(method, url, headers=self.headers(role), json_data=payload)
                    self.assertEqual(response.status_code, 403, response.data)
            self.assertEqual(self.client.request('GET', '/products/categories/', headers=self.headers(role)).status_code, 200)
        for method, url, payload in cases:
            self.assertEqual(self.client.request(method, url, json_data=payload).status_code, 401)

    def test_reorder_persists_including_inactive_categories(self):
        self.categories[0].is_active = 0
        self.db.commit()
        response = self.reorder(self.ids[::-1])
        self.assertEqual(response.status_code, 200, response.data)
        self.db.expire_all()
        response = self.client.request('GET', '/products/categories/')
        self.assertEqual([row['id'] for row in response.data], self.ids[::-1])
        self.assertEqual([row['sort_order'] for row in response.data], [0, 1, 2])
        active = self.client.request('GET', '/products/categories/?active_only=true')
        self.assertEqual([row['id'] for row in active.data], self.ids[:0:-1])

    def test_invalid_order_and_stale_list_leave_every_order_unchanged(self):
        for ids, status in [(self.ids[:-1], 409), (self.ids + [999], 409),
                            ([self.ids[0]] * 3, 422), ([self.ids[0], 999, self.ids[2]], 409),
                            ([], 409), (['1', 2, 3], 422), ([True, 2, 3], 422), ([0, 2, 3], 422)]:
            with self.subTest(ids=ids):
                self.assertEqual(self.reorder(ids).status_code, status)
                self.db.expire_all()
                self.assertEqual([category.sort_order for category in self.categories], [0, 1, 2])
        self.db.add(models.ProductCategory(name='別人新增', is_active=1))
        self.db.commit()
        self.assertEqual(self.reorder(self.ids).status_code, 409)

    def test_transaction_failure_rolls_back_all_positions(self):
        real_commit = self.db.commit

        def fail_after_flush():
            self.db.flush()
            raise RuntimeError('simulated write failure')

        with patch.object(self.db, 'commit', side_effect=fail_after_flush):
            with self.assertRaises(RuntimeError):
                self.reorder(self.ids[::-1])
        self.db.expire_all()
        self.assertEqual([category.sort_order for category in self.categories], [0, 1, 2])
        real_commit()

    def test_create_append_rename_toggle_preserves_product_links(self):
        created = self.client.request('POST', '/products/categories/', headers=self.headers(), json_data={'name': ' 新分類 '})
        self.assertEqual(created.status_code, 200, created.data)
        self.assertGreater(created.data['sort_order'], 2)
        self.assertEqual(created.data['name'], '新分類')
        primary = self.categories[0]
        item = models.Product(name='商品', price=100, stock=3, category_id=primary.id, category=primary.name,
                              additional_categories=[primary, self.categories[1]])
        self.db.add(item)
        self.db.commit()
        response = self.client.request('PUT', f'/products/categories/{primary.id}', headers=self.headers(), json_data={'name': '更名'})
        self.assertEqual(response.status_code, 200)
        self.db.refresh(item)
        self.assertEqual(item.category, '更名')
        for _ in range(2):
            self.assertEqual(self.client.request('PATCH', f'/products/categories/{primary.id}/toggle', headers=self.headers()).status_code, 200)
        self.assertEqual(item.category_id, primary.id)
        self.assertEqual({category.id for category in item.additional_categories}, set(self.ids[:2]))
        self.assertEqual(item.stock, 3)

    def test_rejects_blank_duplicate_long_names_and_bad_status(self):
        for payload in [{'name': ' '}, {'name': '機油'}, {'name': '長' * 51}, {'name': '合法', 'is_active': 2}]:
            with self.subTest(payload=payload):
                response = self.client.request('POST', '/products/categories/', headers=self.headers(), json_data=payload)
                self.assertIn(response.status_code, [400, 422])
        for payload in [{'name': ' '}, {'name': '輪胎'}, {'name': '長' * 51}, {'is_active': 2}]:
            response = self.client.request('PUT', f'/products/categories/{self.ids[0]}', headers=self.headers(), json_data=payload)
            self.assertIn(response.status_code, [400, 422])

    def test_manager_can_assign_existing_but_cannot_create_via_product_form(self):
        for method, url in [('POST', '/products/'), ('PUT', '/products/1')]:
            if method == 'PUT':
                self.db.add(models.Product(id=1, name='商品', price=100))
                self.db.commit()
            response = self.client.request(method, url, headers=self.headers('管理層'),
                                           data={'name': '商品', 'price': '100', 'category': '偷偷新增'})
            self.assertEqual(response.status_code, 403, response.data)
            self.db.rollback()
            self.assertEqual(self.db.query(models.ProductCategory).count(), 3)
        response = self.client.request('POST', '/products/', headers=self.headers('管理層'),
                                       data={'name': '商品', 'price': '100', 'category': '機油'})
        self.assertEqual(response.status_code, 200, response.data)

    def test_inactive_category_retained_on_existing_product_but_rejected_for_new_assignment(self):
        category = self.categories[0]
        item = models.Product(name='舊商品', price=100, category_id=category.id, additional_categories=[category])
        self.db.add(item)
        category.is_active = 0
        self.db.commit()
        response = self.client.request('PUT', f'/products/{item.id}', headers=self.headers('管理層'),
                                       data={'category_id': category.id, 'category_ids': f'[{category.id}]'})
        self.assertEqual(response.status_code, 200, response.data)
        for selection in [{'category_id': category.id}, {'category': category.name}, {'category_ids': f'[{category.id}]'}]:
            response = self.client.request('POST', '/products/', headers=self.headers(), data={'name': '新商品', 'price': 100, **selection})
            self.assertEqual(response.status_code, 422, response.data)
            self.db.rollback()
