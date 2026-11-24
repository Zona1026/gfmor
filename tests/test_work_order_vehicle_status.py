from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import work_orders
from core.config import settings
from db import crud, models
from schemas.work_order import WorkOrderCreate, WorkOrderUpdate
from test_product_pricing_fields import ASGIClient


class WorkOrderVehicleStatusTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        staff = models.Admin(username='staff', full_name='Staff', role='一般', hashed_password='unused')
        self.db.add(staff)
        self.db.commit()
        self.order = crud.create_work_order(self.db, WorkOrderCreate(
            guest_name='Test', guest_phone='0900000000', vehicle_license_plate='TEST-001',
            vehicle_model='Test model', vehicle_mileage=100, responsible_staff_id=staff.id,
            vehicle_status='待內場報價',
        ))
        app = FastAPI()
        app.include_router(work_orders.router, prefix='/work-orders')
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        self.client = ASGIClient(app)
        token = jwt.encode({'sub': 'staff', 'role': 'admin', 'admin_role': '一般',
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        self.headers = {'Authorization': f'Bearer {token}'}

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_vehicle_status_round_trip_is_independent_of_work_order_status(self):
        self.assertEqual(self.order.vehicle_status, '待內場報價')
        original_status = self.order.status
        response = self.client.request('PUT', f'/work-orders/{self.order.id}',
                                       headers=self.headers, json_data={'vehicle_status': '待料中'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['vehicle_status'], '待料中')
        self.assertEqual(response.data['status'], original_status.value)
        self.db.expire_all()
        self.assertEqual(crud.get_work_order(self.db, self.order.id).vehicle_status, '待料中')

    def test_reviewed_orders_can_update_operational_vehicle_status_and_partial_saves_preserve_it(self):
        self.order.supervisor_reviewed_at = datetime.now()
        self.db.commit()
        saved = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(vehicle_status='待料中'))
        self.assertEqual(saved.vehicle_status, '待料中')
        self.assertIsNotNone(saved.supervisor_reviewed_at)
        saved = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(notes='Note'))
        self.assertEqual(saved.vehicle_status, '待料中')
        saved = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(vehicle_status=None))
        self.assertIsNone(saved.vehicle_status)

    def test_status_is_optional_and_rejects_unknown_choices(self):
        self.assertIsNone(WorkOrderCreate().vehicle_status)
        for schema in (WorkOrderCreate, WorkOrderUpdate):
            with self.assertRaises(ValidationError):
                schema(vehicle_status='其他狀態')
            for choice in ['待內場報價', '待料中', '料到待施工', '施工中', '料件追加', '已完工']:
                self.assertEqual(schema(vehicle_status=choice).vehicle_status, choice)

    def test_migration_preserves_existing_orders(self):
        order_id = self.order.id
        self.db.close()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261124_0037_work_order_vehicle_status.py'
        spec = importlib.util.spec_from_file_location('vehicle_status_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT vehicle_license_plate, vehicle_status FROM work_orders WHERE id=:id'),
                                                {'id': order_id}).one(), ('TEST-001', None))
