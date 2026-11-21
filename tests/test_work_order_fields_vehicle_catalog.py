from datetime import date, datetime, timedelta, timezone
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

from api.endpoints import products
from core.config import settings
from db import crud, models
from schemas.work_order import WorkOrderCreate, WorkOrderUpdate
from test_product_pricing_fields import ASGIClient


class WorkOrderFieldsVehicleCatalogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = models.User(google_id='member', name='Customer', email='test@example.com')
        self.motor = models.Motor(google_id='member', license_plate='TEST-001', model_name='Original',
                                  brand='Original brand', vin='ENGINE-001', mileage=1000)
        self.db.add_all([self.user, self.motor])
        self.db.commit()
        app = FastAPI()
        app.include_router(products.router, prefix='/products')
        app.dependency_overrides[products.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def headers(self, role='一般'):
        token = jwt.encode({'sub': 'tester', 'role': 'admin', 'admin_role': role,
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return {'Authorization': f'Bearer {token}'}

    def create(self, **kwargs):
        return crud.create_work_order(self.db, WorkOrderCreate(
            google_id='member', motor_id=self.motor.id, responsible_staff='Tester',
            vehicle_mileage=1500, **kwargs))

    def test_technician_default_and_validation(self):
        order = self.create()
        self.assertEqual(order.technician, '江子暢')
        self.assertEqual(crud.update_work_order(self.db, order.id, WorkOrderUpdate(technician='林書宇')).technician, '林書宇')
        with self.assertRaises(ValidationError):
            WorkOrderUpdate(technician='other')

    def test_receiving_person_links_to_accounts_independently_of_technician(self):
        for index, (name, role) in enumerate([('江子暢', '一般'), ('林侑羽', '最高級'), ('老闆/闆娘', '管理層')]):
            with self.subTest(role=role):
                account = models.Admin(username=f'receiver-{index}', full_name=name,
                                       role=role, hashed_password='not-used')
                self.db.add(account)
                self.db.commit()
                order = crud.create_work_order(self.db, WorkOrderCreate(
                    google_id='member', motor_id=self.motor.id, vehicle_mileage=1500,
                    responsible_staff_id=account.id))
                self.assertEqual(order.responsible_staff_id, account.id)
                self.assertEqual(order.responsible_staff, name)
                self.assertEqual(order.technician, '江子暢')
                updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(technician='林書宇'))
                self.assertEqual(updated.responsible_staff_id, account.id)
                self.assertEqual(updated.technician, '林書宇')

    def test_receiving_person_can_switch_accounts_without_changing_technician(self):
        first = models.Admin(username='first', full_name='江子暢', role='一般', hashed_password='not-used')
        second = models.Admin(username='second', full_name='林侑羽', role='最高級', hashed_password='not-used')
        self.db.add_all([first, second])
        self.db.commit()
        order = crud.create_work_order(self.db, WorkOrderCreate(
            google_id='member', motor_id=self.motor.id, vehicle_mileage=1500,
            responsible_staff_id=first.id, technician='老闆'))
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(responsible_staff_id=second.id))
        self.assertEqual(updated.responsible_staff_id, second.id)
        self.assertEqual(updated.responsible_staff, '林侑羽')
        self.assertEqual(updated.technician, '老闆')

    def test_vehicle_snapshot_edits_survive_selection_without_changing_member_vehicle(self):
        order = self.create()
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(
            motor_id=self.motor.id, vehicle_license_plate='SNAPSHOT', vehicle_model='Free model',
            vehicle_brand='Free brand', vehicle_vin='Free engine'))
        self.assertEqual((updated.vehicle_license_plate, updated.vehicle_model, updated.vehicle_brand, updated.vehicle_vin),
                         ('SNAPSHOT', 'Free model', 'Free brand', 'Free engine'))
        self.db.refresh(self.motor)
        self.assertEqual((self.motor.license_plate, self.motor.model_name, self.motor.brand, self.motor.vin),
                         ('TEST-001', 'Original', 'Original brand', 'ENGINE-001'))
        self.assertEqual(self.db.query(models.ProductVehicleModel).count(), 0)

    def test_guest_snapshot_edit_does_not_change_vehicle(self):
        order = crud.create_work_order(self.db, WorkOrderCreate(
            guest_name='Guest', guest_phone='0900000000', vehicle_license_plate='GUEST-01',
            vehicle_model='Original', vehicle_mileage=100, responsible_staff='Tester'))
        vehicle = order.guest_motor
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(
            guest_motor_id=vehicle.id, vehicle_model='Edited', vehicle_license_plate='GUEST-EDIT'))
        self.assertEqual(updated.vehicle_model, 'Edited')
        self.db.refresh(vehicle)
        self.assertEqual((vehicle.model_name, vehicle.license_plate), ('Original', 'GUEST-01'))

    def test_completion_correction_keeps_actual_completion_consumption_and_future_point_basis(self):
        order = self.create()
        actual = datetime(2026, 10, 10, 12)
        order.completed_at = actual
        order.consumption_date = date(2026, 10, 10)
        order.status = models.WorkOrderStatus.COMPLETED
        self.db.commit()
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(completed_date=date(2026, 10, 9)))
        self.assertEqual(updated.completed_date_override, date(2026, 10, 9))
        self.assertEqual(updated.completed_at, actual)
        self.assertEqual(updated.consumption_date, date(2026, 10, 10))
        from db.points import _work_order_point_date
        self.assertEqual(_work_order_point_date(updated), actual)
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(notes='Later save'))
        self.assertEqual(_work_order_point_date(updated), actual)

    def test_unfinished_order_cannot_set_completion_date(self):
        order = self.create()
        with self.assertRaisesRegex(ValueError, '未完工'):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(completed_date=date(2026, 10, 9)))

    def test_member_and_guest_schedules_are_idempotent(self):
        order = self.create(vehicle_is_new=True)
        guest = crud.create_work_order(self.db, WorkOrderCreate(
            guest_name='Guest', guest_phone='0900000000', vehicle_license_plate='GUEST-01', vehicle_model='Model',
            vehicle_mileage=100, responsible_staff='Tester', vehicle_is_new=True))
        for current in (order, guest):
            count = self.db.query(models.NewVehicleMaintenanceRecord).count()
            crud.update_work_order(self.db, current.id, WorkOrderUpdate(vehicle_is_new=True))
            self.assertEqual(self.db.query(models.NewVehicleMaintenanceRecord).count(), count)
        self.assertGreater(self.db.query(models.NewVehicleMaintenanceRecord).filter_by(motor_id=self.motor.id).count(), 0)
        self.assertGreater(self.db.query(models.NewVehicleMaintenanceRecord).filter_by(guest_motor_id=guest.guest_motor_id).count(), 0)

    def test_reviewed_order_cannot_create_schedule(self):
        order = self.create()
        order.supervisor_reviewed_at = datetime.now()
        self.db.commit()
        with self.assertRaisesRegex(ValueError, '主管已審核'):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(vehicle_is_new=True))

    def test_catalog_permissions_inactive_duplicate_and_historical_text(self):
        endpoint = '/products/admin/vehicle-models'
        self.assertEqual(self.client.request('POST', endpoint, headers=self.headers(), json_data={'name': 'Original'}).status_code, 200)
        row = self.db.query(models.ProductVehicleModel).one()
        order = self.create()
        patch_endpoint = f'{endpoint}/{row.id}'
        self.assertEqual(self.client.request('PATCH', patch_endpoint, headers=self.headers(), json_data={'name': 'Renamed'}).status_code, 403)
        for changes in ({'name': 'Renamed'}, {'is_active': False}):
            response = self.client.request('PATCH', patch_endpoint, headers=self.headers('管理層'), json_data=changes)
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.request('GET', endpoint, headers=self.headers()).data, [])
        self.assertEqual(self.client.request('POST', endpoint, headers=self.headers(), json_data={'name': 'Renamed'}).status_code, 409)
        self.assertEqual(self.client.request('GET', endpoint + '/manage', headers=self.headers()).data[0]['is_active'], False)
        self.db.refresh(order)
        self.assertEqual(order.vehicle_model, 'Original')

    def test_migration_backfills_legacy_options_and_preserves_old_work_order(self):
        order = self.create(vehicle_model='Historical model')
        self.db.add(models.Product(name='Part', price=1, vehicle_models=[' Legacy ', 'Original']))
        self.db.commit()
        order_id = order.id
        self.db.close()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261122_0034_work_order_fields_vehicle_catalog.py'
        spec = importlib.util.spec_from_file_location('fields_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, 'op', operations):
                migration.downgrade()
                migration.upgrade()
            self.assertEqual(set(connection.execute(text('SELECT name FROM product_vehicle_models')).scalars()),
                             {'通用', 'Legacy', 'Original', 'Historical model'})
            self.assertEqual(connection.execute(text('SELECT technician, vehicle_model FROM work_orders WHERE id=:id'),
                                                {'id': order_id}).one(), (None, 'Historical model'))
