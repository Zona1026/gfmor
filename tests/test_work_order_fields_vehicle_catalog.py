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

    def test_new_order_accepts_manual_completion_date_without_completing_order(self):
        order = self.create(completed_date=date(2026, 12, 1))
        self.assertEqual(order.completed_date_override, date(2026, 12, 1))
        self.assertIsNone(order.completed_at)
        self.assertNotEqual(order.status, models.WorkOrderStatus.COMPLETED)
        self.assertEqual(self.db.query(models.PointTransaction).count(), 0)

    def test_unfinished_order_can_set_change_and_clear_completion_date(self):
        order = self.create()
        consumption_date = order.consumption_date
        for value in [date(2026, 10, 9), date(2026, 12, 1), None]:
            with self.subTest(value=value):
                updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(completed_date=value))
                self.assertEqual(updated.completed_date_override, value)
                self.assertIsNone(updated.completed_at)
                self.assertEqual(updated.consumption_date, consumption_date)

    def test_completed_order_still_rejects_empty_completion_date(self):
        order = self.create()
        order.completed_at = datetime(2026, 10, 10, 12)
        self.db.commit()
        with self.assertRaisesRegex(ValueError, '完工日期不可清空'):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(completed_date=None))

    def test_unrelated_save_preserves_manual_completion_date(self):
        order = self.create(completed_date=date(2026, 10, 9))
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(notes='Keep date'))
        self.assertEqual(updated.completed_date_override, date(2026, 10, 9))

    def test_actual_completion_keeps_manual_display_date_and_uses_actual_point_date(self):
        from db.points import _work_order_point_date
        for manual in [None, date(2026, 10, 9)]:
            with self.subTest(manual=manual):
                order = self.create(completed_date=manual)
                actual = datetime(2026, 10, 10, 12)
                crud._mark_work_order_completed(order, actual)
                self.assertEqual(order.completed_date_override, manual)
                self.assertEqual(order.completed_at, actual)
                self.assertEqual(order.consumption_date, date(2026, 10, 10))
                self.assertEqual(_work_order_point_date(order), actual)

    def test_invalid_manual_completion_date_is_rejected(self):
        for schema in [WorkOrderCreate, WorkOrderUpdate]:
            with self.subTest(schema=schema):
                with self.assertRaises(ValidationError):
                    schema(completed_date='2026-02-30')

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

    def test_vehicle_brand_options_use_existing_data_and_active_catalog(self):
        self.motor.brand = ' SYM '
        order = self.create(vehicle_brand='YAMAHA')
        self.db.add_all([
            models.GuestCustomer(name='Guest', phone='0900000000', motors=[models.GuestMotor(
                license_plate='GUEST-02', brand='HONDA')]),
            models.ProductVehicleModel(name='Active', brand_type='  Type A  '),
            models.ProductVehicleModel(name='Duplicate', brand_type='Type A'),
            models.ProductVehicleModel(name='Blank', brand_type='  '),
            models.ProductVehicleModel(name='Disabled', brand_type='Hidden', is_active=False),
        ])
        self.db.commit()
        endpoint = '/products/admin/vehicle-brand-options'
        response = self.client.request('GET', endpoint, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {'brands': ['HONDA', 'SYM', 'YAMAHA'], 'brand_types': ['Type A']})
        self.assertIn(self.client.request('GET', endpoint).status_code, (401, 403))

    def test_work_order_brand_type_snapshot_survives_changes_and_can_clear(self):
        order = self.create(vehicle_brand_type='  Original type  ')
        self.assertEqual(order.vehicle_brand_type, 'Original type')
        updated = crud.update_work_order(self.db, order.id, WorkOrderUpdate(
            motor_id=self.motor.id, vehicle_brand_type='  Edited type  '))
        self.assertEqual(updated.vehicle_brand_type, 'Edited type')
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(notes='Unrelated save'))
        self.assertEqual(updated.vehicle_brand_type, 'Edited type')
        self.db.refresh(self.motor)
        self.assertEqual(self.motor.brand, 'Original brand')
        self.assertEqual(crud.update_work_order(self.db, order.id, WorkOrderUpdate(vehicle_brand_type='')).vehicle_brand_type, None)
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(vehicle_brand_type='Again'))
        self.assertIsNone(crud.update_work_order(self.db, order.id, WorkOrderUpdate(vehicle_brand_type=None)).vehicle_brand_type)

    def test_reviewed_order_rejects_brand_type_changes(self):
        order = self.create(vehicle_brand_type='Original')
        order.supervisor_reviewed_at = datetime.now()
        self.db.commit()
        with self.assertRaisesRegex(ValueError, '主管已審核'):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(vehicle_brand_type='Other'))
        for schema in (WorkOrderCreate, WorkOrderUpdate):
            with self.assertRaises(ValidationError):
                schema(vehicle_brand_type='x' * 201)

    def test_work_order_brand_type_migration_preserves_existing_snapshot(self):
        order = self.create(vehicle_brand='SYM', vehicle_model='Legacy')
        order_id = order.id
        self.db.close()
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261123_0036_work_order_brand_type.py'
        spec = importlib.util.spec_from_file_location('work_order_brand_type_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, 'op', operations):
                migration.downgrade()
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT vehicle_brand, vehicle_model, vehicle_brand_type FROM work_orders WHERE id=:id'),
                                                {'id': order_id}).one(), ('SYM', 'Legacy', None))

    def test_catalog_brand_type_create_update_clear_and_permissions(self):
        endpoint = '/products/admin/vehicle-models'
        response = self.client.request('POST', endpoint, headers=self.headers(),
                                       json_data={'name': 'Test model', 'brand_type': '  YAMAHA 型式  '})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, 'Test model')
        row = self.db.query(models.ProductVehicleModel).one()
        self.assertEqual(row.brand_type, 'YAMAHA 型式')
        patch_endpoint = f'{endpoint}/{row.id}'
        self.assertEqual(self.client.request('PATCH', patch_endpoint, headers=self.headers(),
                                            json_data={'brand_type': 'Other'}).status_code, 403)
        for value, expected in [('  HONDA 型式  ', 'HONDA 型式'), ('  ', None), ('New', 'New'), (None, None)]:
            response = self.client.request('PATCH', patch_endpoint, headers=self.headers('管理層'),
                                           json_data={'brand_type': value})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['brand_type'], expected)
            self.assertEqual(self.client.request('GET', endpoint + '/manage', headers=self.headers()).data[0]['brand_type'], expected)
        self.assertEqual(self.client.request('GET', endpoint, headers=self.headers()).data, ['Test model'])

    def test_catalog_brand_type_optional_validation_and_unrelated_update(self):
        endpoint = '/products/admin/vehicle-models'
        self.client.request('POST', endpoint, headers=self.headers(), json_data={'name': 'Legacy'})
        row = self.db.query(models.ProductVehicleModel).one()
        self.assertIsNone(row.brand_type)
        row.brand_type = 'Preserved'
        self.db.commit()
        patch_endpoint = f'{endpoint}/{row.id}'
        for changes in ({'name': 'Renamed'}, {'is_active': False}):
            response = self.client.request('PATCH', patch_endpoint, headers=self.headers('管理層'), json_data=changes)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['brand_type'], 'Preserved')
        for method, path, data in [('POST', endpoint, {'name': 'Too long', 'brand_type': 'x' * 201}),
                                   ('PATCH', patch_endpoint, {'brand_type': 'x' * 201}),
                                   ('PATCH', patch_endpoint, {'name': None}),
                                   ('PATCH', patch_endpoint, {'is_active': None})]:
            self.assertEqual(self.client.request(method, path, headers=self.headers('管理層'), json_data=data).status_code, 422)

    def test_brand_type_migration_preserves_existing_catalog(self):
        path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261123_0035_vehicle_model_brand_type.py'
        spec = importlib.util.spec_from_file_location('brand_type_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            with patch.object(migration, 'op', operations):
                migration.downgrade()
                connection.execute(text("INSERT INTO product_vehicle_models (name, is_active) VALUES ('Legacy', 1)"))
                migration.upgrade()
            self.assertEqual(connection.execute(text('SELECT name, brand_type, is_active FROM product_vehicle_models')).one(),
                             ('Legacy', None, 1))

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
