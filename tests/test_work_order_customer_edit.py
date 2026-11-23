from datetime import date, datetime, timedelta, timezone
import unittest

from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import work_orders
from core.config import settings
from db import models
from test_product_pricing_fields import ASGIClient


class WorkOrderCustomerEditTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.member = models.User(google_id='member', name='Original', phone='0900000000', email='member@example.com')
        self.guest = models.GuestCustomer(name='', phone='')
        self.db.add_all([self.member, self.guest])
        self.db.commit()
        app = FastAPI()
        app.include_router(work_orders.router, prefix='/work-orders')
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def headers(self, role='一般', token_role='admin'):
        token = jwt.encode({'sub': 'staff', 'role': token_role, 'admin_role': role,
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {'Authorization': f'Bearer {token}'}

    def order(self, **kwargs):
        order = models.WorkOrder(ordered_date=date.today(), consumption_date=date.today(), **kwargs)
        self.db.add(order)
        self.db.commit()
        return order

    def save(self, order, data, **kwargs):
        return self.client.request('PATCH', f'/work-orders/{order.id}/customer', json_data=data,
                                   headers=kwargs.get('headers', self.headers()))

    def test_general_staff_can_fill_guest_profile_and_modify_it_again(self):
        order = self.order(guest_customer_id=self.guest.id, customer_name='', customer_phone='', total_amount=430)
        for name, phone in [('  王先生  ', '  0902103130  '), ('王小姐', '0911111111')]:
            response = self.save(order, {'name': name, 'phone': phone})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual((response.data['customer_name'], response.data['customer_phone']), (name.strip(), phone.strip()))
            self.db.refresh(self.guest)
            self.assertEqual((self.guest.name, self.guest.phone), (name.strip(), phone.strip()))
            self.assertEqual(response.data['total_amount'], 430)
            self.assertEqual(response.data['status'], order.status.value)
            self.assertEqual(self.db.query(models.PointTransaction).count(), 0)

    def test_member_edits_return_saved_name_and_preserve_customer_binding(self):
        order = self.order(google_id=self.member.google_id, customer_name='Old name')
        other = self.order(guest_customer_id=self.guest.id, customer_name='Other')
        response = self.save(order, {'name': '陳先生', 'phone': '0922222222'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['customer_name'], '陳先生')
        self.assertEqual(response.data['google_id'], 'member')
        self.db.refresh(self.member)
        self.db.refresh(other)
        self.assertEqual((self.member.name, self.member.phone), ('陳先生', '0922222222'))
        self.assertEqual(other.customer_name, 'Other')

    def test_reviewed_order_customer_information_remains_editable(self):
        order = self.order(guest_customer_id=self.guest.id, supervisor_reviewed_at=datetime.now())
        response = self.save(order, {'name': '客人', 'phone': '0900000000'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(order.supervisor_reviewed_at)

    def test_customer_edit_rejects_unauthenticated_and_member_tokens(self):
        order = self.order(guest_customer_id=self.guest.id)
        for headers in ({}, self.headers(token_role='member')):
            self.assertEqual(self.save(order, {'name': 'Forbidden', 'phone': ''}, headers=headers).status_code, 401)
        self.db.refresh(self.guest)
        self.assertEqual(self.guest.name, '')

    def test_validation_missing_deleted_and_merged_orders(self):
        order = self.order(google_id=self.member.google_id)
        self.assertEqual(self.save(order, {'name': 'x' * 11, 'phone': ''}).status_code, 400)
        self.assertEqual(self.save(order, {'name': 'Name', 'phone': 'x' * 21}).status_code, 422)
        self.assertEqual(self.save(order, {'name': None, 'phone': ''}).status_code, 422)
        self.db.refresh(self.member)
        self.assertEqual(self.member.name, 'Original')
        order.deleted_at = datetime.now()
        self.db.commit()
        self.assertEqual(self.save(order, {'name': 'Name', 'phone': ''}).status_code, 400)
        guest_order = self.order(guest_customer_id=self.guest.id)
        self.guest.merged_at = datetime.now()
        self.db.commit()
        self.assertEqual(self.save(guest_order, {'name': 'Name', 'phone': ''}).status_code, 400)
        self.assertEqual(self.client.request('PATCH', '/work-orders/999999/customer', headers=self.headers(),
                                            json_data={'name': 'Name', 'phone': ''}).status_code, 404)
