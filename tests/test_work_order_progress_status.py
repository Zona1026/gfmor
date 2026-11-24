from datetime import datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import quote

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import crud, models
from api.endpoints import work_orders
from schemas.work_order import WorkOrderCreate, WorkOrderUpdate, WorkOrder
from test_product_pricing_fields import ASGIClient


CHOICES = ['待廠商回應', '已報價待客確認', '待訂購', '待到貨', '部分到貨', '全數到貨', '已出貨', '已完單']


class WorkOrderProgressStatusTest(unittest.TestCase):
    def test_migration_graph_has_one_head(self):
        migrations = Path(__file__).resolve().parents[1] / 'migrations'
        self.assertEqual(len(ScriptDirectory(str(migrations)).get_heads()), 1)

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
        ))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_choices_round_trip_without_changing_approval_or_vehicle_state(self):
        self.order.status = models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING
        self.order.supervisor_reviewed_at = datetime.now()
        self.order.vehicle_status = '待料中'
        self.db.commit()
        for choice in CHOICES:
            order = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(progress_status=choice))
            self.assertEqual(WorkOrder.model_validate(order).progress_status, choice)
            self.assertEqual(order.status, models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING)
            self.assertEqual(order.vehicle_status, '待料中')
        crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(notes='preserve'))
        self.assertEqual(self.order.progress_status, '已完單')
        crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(progress_status=None))
        self.assertIsNone(self.order.progress_status)

    def test_create_filter_and_validation(self):
        for choice in CHOICES:
            self.assertEqual(WorkOrderCreate(progress_status=choice).progress_status, choice)
        with self.assertRaises(ValidationError):
            WorkOrderUpdate(progress_status='待主管確認')
        self.assertEqual([o.id for o in crud.get_work_orders(self.db, progress_status='blank')], [self.order.id])
        crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(progress_status='部分到貨'))
        self.assertEqual([o.id for o in crud.get_work_orders(self.db, progress_status='部分到貨')], [self.order.id])
        self.assertEqual(crud.get_work_orders(self.db, progress_status='blank'), [])
        self.assertEqual(crud.get_work_orders(self.db, progress_status='已出貨'), [])

    def test_completion_sets_final_progress_after_pending_progress_payload(self):
        self.order.supervisor_reviewed_at = datetime.now()
        self.db.commit()
        order = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(
            status=models.WorkOrderStatus.COMPLETED, progress_status='已出貨'))
        self.assertEqual(order.progress_status, '已完單')
        self.assertIsNotNone(order.completed_at)

    def test_list_api_filters_and_serializes_progress(self):
        app = FastAPI()
        app.include_router(work_orders.router, prefix='/work-orders')
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        app.dependency_overrides[work_orders.require_admin] = lambda: object()
        client = ASGIClient(app)
        crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(progress_status='待廠商回應'))
        response = client.request('GET', '/work-orders/?progress_status=' + quote('待廠商回應'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([o['progress_status'] for o in response.data], ['待廠商回應'])
        response = client.request('GET', '/work-orders/?progress_status=blank')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, [])

    def test_migration_leaves_supervisor_pending_blank_and_preserves_workflow(self):
        self.db.close()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261125_0038_work_order_progress_status.py'
        spec = importlib.util.spec_from_file_location('progress_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            with patch.object(migration, 'op', Operations(MigrationContext.configure(connection))):
                migration.downgrade()
                for status, expected in [('SUPERVISOR_APPROVAL_PENDING', None),
                                         ('CUSTOMER_CONFIRMATION_PENDING', '已報價待客確認'),
                                         ('COMPLETED', '已完單'), ('IN_PROGRESS', None)]:
                    connection.execute(text('UPDATE work_orders SET status=:status'), {'status': status})
                    migration.upgrade()
                    self.assertEqual(connection.execute(text('SELECT status, progress_status FROM work_orders')).one(),
                                     (status, expected))
                    migration.downgrade()


if __name__ == '__main__':
    unittest.main()
