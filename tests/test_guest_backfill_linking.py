import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.endpoints.guest_customers import create_guest_customer
from db import crud, models
from db.database import Base
from schemas.guest_customer import GuestCustomerCreate
from schemas.work_order import HistoricalWorkOrderCreate, WorkOrderCreate


class GuestBackfillLinkingTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def _work_order_input(self, *, name, phone, plate):
        return WorkOrderCreate(
            guest_name=name,
            guest_phone=phone,
            vehicle_license_plate=plate,
            vehicle_model="CUE 00",
            vehicle_mileage=1000,
            responsible_staff="江子暘",
        )

    def _work_order_record(self):
        return models.WorkOrder(responsible_staff="江子暘")

    def test_same_placeholder_phone_with_different_names_creates_separate_guests(self):
        first_work_order = self._work_order_record()
        crud._hydrate_direct_customer(
            self.db,
            first_work_order,
            self._work_order_input(name="陳世寧", phone="待補", plate="MLR-2752"),
        )

        second_work_order = self._work_order_record()
        crud._hydrate_direct_customer(
            self.db,
            second_work_order,
            self._work_order_input(name="洪振峰", phone="待補", plate="395-KLS"),
        )

        guests = self.db.query(models.GuestCustomer).order_by(models.GuestCustomer.id).all()
        self.assertEqual([guest.name for guest in guests], ["陳世寧", "洪振峰"])
        self.assertNotEqual(first_work_order.guest_customer_id, second_work_order.guest_customer_id)

        motors_by_guest = {
            guest.name: [motor.license_plate for motor in guest.motors]
            for guest in guests
        }
        self.assertEqual(motors_by_guest["陳世寧"], ["MLR-2752"])
        self.assertEqual(motors_by_guest["洪振峰"], ["395-KLS"])

    def test_guest_name_and_phone_are_optional_for_direct_work_order(self):
        work_order = self._work_order_record()
        crud._hydrate_direct_customer(
            self.db,
            work_order,
            self._work_order_input(name="", phone="", plate="MLR-2752"),
        )

        guests = self.db.query(models.GuestCustomer).all()
        self.assertEqual(len(guests), 1)
        self.assertEqual(guests[0].name, "")
        self.assertEqual(guests[0].phone, "")
        self.assertEqual(work_order.guest_customer_id, guests[0].id)
        self.assertEqual(work_order.customer_name, "")
        self.assertEqual(work_order.customer_phone, "")
        self.assertEqual([motor.license_plate for motor in guests[0].motors], ["MLR-2752"])

    def test_same_name_and_phone_reuses_existing_guest(self):
        first_work_order = self._work_order_record()
        crud._hydrate_direct_customer(
            self.db,
            first_work_order,
            self._work_order_input(name="陳世寧", phone="待補", plate="MLR-2752"),
        )

        second_work_order = self._work_order_record()
        crud._hydrate_direct_customer(
            self.db,
            second_work_order,
            self._work_order_input(name="陳世寧", phone="待補", plate="PDH-3099"),
        )

        guests = self.db.query(models.GuestCustomer).all()
        self.assertEqual(len(guests), 1)
        self.assertEqual(first_work_order.guest_customer_id, second_work_order.guest_customer_id)
        self.assertEqual(
            sorted(motor.license_plate for motor in guests[0].motors),
            ["MLR-2752", "PDH-3099"],
        )

    def test_historical_backfill_payment_method_is_optional(self):
        work_order = HistoricalWorkOrderCreate(
            guest_name="陳世寧",
            guest_phone="待補",
            vehicle_license_plate="MLR-2752",
            vehicle_model="CUE 00",
            vehicle_mileage=1000,
            responsible_staff="江子暘",
            ordered_date="2026-09-30",
            completed_date="2026-10-03",
            paid_date="2026-10-03",
            backfill_reason="補登舊紀錄",
            line_items=[{
                "type": "SERVICE",
                "name": "保養",
                "quantity": 1,
                "unit_price": 200,
            }],
        )
        self.assertIsNone(work_order.payment_method)

        blank_payload = work_order.model_dump()
        blank_payload["payment_method"] = ""
        blank_method = HistoricalWorkOrderCreate(**blank_payload)
        self.assertEqual(blank_method.payment_method, "")

    def test_guest_customer_create_does_not_overwrite_same_phone_different_name(self):
        first = create_guest_customer(
            GuestCustomerCreate(name="陳世寧", phone="待補"),
            admin={},
            db=self.db,
        )
        second = create_guest_customer(
            GuestCustomerCreate(name="洪振峰", phone="待補"),
            admin={},
            db=self.db,
        )

        guests = self.db.query(models.GuestCustomer).order_by(models.GuestCustomer.id).all()
        self.assertEqual([guest.name for guest in guests], ["陳世寧", "洪振峰"])
        self.assertNotEqual(first.id, second.id)

    def test_guest_customer_create_does_not_merge_blank_profiles(self):
        first = create_guest_customer(GuestCustomerCreate(), admin={}, db=self.db)
        second = create_guest_customer(GuestCustomerCreate(), admin={}, db=self.db)

        guests = self.db.query(models.GuestCustomer).order_by(models.GuestCustomer.id).all()
        self.assertEqual(len(guests), 2)
        self.assertNotEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
