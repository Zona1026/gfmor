from datetime import date, datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import crud, models
from schemas.work_order import HistoricalWorkOrderCreate, WorkOrderCreate, WorkOrderUpdate


class WorkOrderMileageTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = models.User(google_id='member', name='Customer', email='member@example.com')
        self.motor = models.Motor(google_id='member', license_plate='TEST-001', model_name='Test', mileage=1000)
        self.other_motor = models.Motor(google_id='member', license_plate='TEST-002', model_name='Other', mileage=500)
        self.db.add_all([self.user, self.motor, self.other_motor])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def create(self, mileage=1500, **kwargs):
        return crud.create_work_order(self.db, WorkOrderCreate(
            google_id='member', motor_id=self.motor.id, responsible_staff='Tester',
            vehicle_mileage=mileage, **kwargs))

    def vehicle_mileage(self, motor=None):
        self.db.expire_all()
        return (motor or self.motor).mileage

    def test_creation_updates_member_vehicle_and_next_order_inherits_mileage(self):
        self.create(1500)
        self.assertEqual(self.vehicle_mileage(), 1500)
        self.assertEqual(self.other_motor.mileage, 500)
        result = self.create(None)
        self.assertEqual(result.vehicle_mileage, 1500)
        search = crud.get_users_by_name(self.db, 'TEST-001')
        self.assertEqual(next(m.mileage for m in search[0].motors if m.id == self.motor.id), 1500)

    def test_editing_mileage_updates_vehicle_without_downgrading_for_old_work_orders(self):
        old = self.create(1500)
        recent = self.create(2500)
        crud.update_work_order(self.db, recent.id, WorkOrderUpdate(vehicle_mileage=3000))
        self.assertEqual(self.vehicle_mileage(), 3000)
        result = crud.update_work_order(self.db, old.id, WorkOrderUpdate(vehicle_mileage=1800))
        self.assertEqual(result.vehicle_mileage, 1800)
        self.assertEqual(self.vehicle_mileage(), 3000)

    def test_booking_conversion_uses_entered_mileage_and_syncs_vehicle(self):
        booking = models.Booking(google_id='member', motor_id=self.motor.id,
                                 booking_time=datetime.now(), category=models.BookingCategory.MAINTENANCE,
                                 status=models.BookingStatus.PENDING)
        self.db.add(booking)
        self.db.commit()
        result = self.create(2000, booking_id=booking.id)
        self.assertEqual(result.vehicle_mileage, 2000)
        self.assertEqual(self.vehicle_mileage(), 2000)

    def test_zero_mileage_is_recorded_for_a_vehicle_with_no_prior_mileage(self):
        self.motor.mileage = None
        self.db.commit()
        result = self.create(0)
        self.assertEqual(result.vehicle_mileage, 0)
        self.assertEqual(self.vehicle_mileage(), 0)

    def test_switching_vehicles_only_updates_the_selected_vehicle(self):
        order = self.create(1500)
        result = crud.update_work_order(self.db, order.id, WorkOrderUpdate(
            motor_id=self.other_motor.id, vehicle_mileage=800))
        self.assertEqual(result.motor_id, self.other_motor.id)
        self.assertEqual(self.vehicle_mileage(self.other_motor), 800)
        self.assertEqual(self.motor.mileage, 1500)

    def test_historical_backfill_does_not_reduce_current_vehicle_mileage(self):
        self.motor.mileage = 3000
        self.db.commit()
        result = crud.create_historical_work_order(self.db, HistoricalWorkOrderCreate(
            google_id='member', motor_id=self.motor.id, responsible_staff='Tester',
            vehicle_mileage=1500, ordered_date=date(2026, 1, 1),
            completed_date=date(2026, 1, 2), paid_date=date(2026, 1, 2),
            backfill_reason='Test import', award_points=False,
            line_items=[{'type': 'LABOR', 'name': 'Service', 'quantity': 1, 'unit_price': 100}],
        ), actor='Tester')
        self.assertEqual(result.vehicle_mileage, 1500)
        self.assertEqual(self.vehicle_mileage(), 3000)

    def test_failed_creation_can_rollback_vehicle_and_order_together(self):
        with patch('db.crud.get_work_order', side_effect=RuntimeError('not used')):
            with patch.object(self.db, 'commit', side_effect=RuntimeError('commit failed')):
                with self.assertRaises(RuntimeError):
                    self.create(2000)
        self.db.rollback()
        self.assertEqual(self.vehicle_mileage(), 1000)
        self.assertEqual(self.db.query(models.WorkOrder).count(), 0)

    def test_existing_work_orders_backfill_only_valid_higher_member_mileage(self):
        self.create(2400)
        self.create(2000)
        canceled = self.create(9000)
        canceled.status = models.WorkOrderStatus.CANCELED
        deleted = self.create(10000)
        deleted.deleted_at = datetime.now()
        self.motor.mileage = 1000
        self.db.commit()
        migration_path = Path(__file__).resolve().parents[1] / 'migrations/versions/20261010_0025_member_vehicle_mileage.py'
        spec = importlib.util.spec_from_file_location('mileage_migration', migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration._backfill_member_mileage(self.db.connection())
        self.db.commit()
        self.assertEqual(self.vehicle_mileage(), 2400)
        self.assertEqual(self.other_motor.mileage, 500)
        migration._backfill_member_mileage(self.db.connection())
        self.db.commit()
        self.assertEqual(self.vehicle_mileage(), 2400)


if __name__ == '__main__':
    unittest.main()
