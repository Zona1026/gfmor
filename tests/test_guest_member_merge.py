from datetime import date, datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import crud, models
from schemas.motor import MotorCreate, MotorUpdate
from schemas.user import UserUpdate


class GuestMemberMergeTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.member = models.User(
            google_id="member", name="Member", email="member@example.com",
            phone="0912345678", cumulative_consumption=0,
        )
        self.db.add(self.member)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def guest(self, phone="other", plates=()):
        guest = models.GuestCustomer(name="Guest", phone=phone)
        self.db.add(guest)
        self.db.flush()
        for plate in plates:
            self.db.add(models.GuestMotor(guest_customer_id=guest.id, license_plate=plate))
        order = models.Order(
            guest_customer_id=guest.id, total_amount=100,
            status=models.OrderStatus.COMPLETED, recipient_name="Guest",
            recipient_phone=phone, shipping_address="Shop",
        )
        self.db.add(order)
        self.db.commit()
        return guest, order

    def motor(self, plate="ABC-1234", status=None):
        motor = models.Motor(
            google_id=self.member.google_id, license_plate=plate, status=status,
        )
        self.db.add(motor)
        self.db.commit()
        return motor

    def test_phone_alone_merges_different_name(self):
        guest, order = self.guest(phone=self.member.phone)
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        self.assertEqual(order.google_id, "member")
        self.assertIsNone(order.guest_customer_id)
        self.assertEqual(self.member.cumulative_consumption, 100)

    def test_plate_alone_merges_with_no_member_phone(self):
        self.member.phone = None
        self.motor()
        guest, order = self.guest(plates=("abc1234",))
        crud.update_user(self.db, "member", UserUpdate(phone=None))
        self.assertEqual(order.google_id, "member")
        self.assertEqual(self.db.query(models.Motor).count(), 1)

    def test_plate_formats_reuse_member_motor_and_link_work_order(self):
        motor = self.motor()
        guest, order = self.guest(plates=(" \tabc 1234\n", "XYZ-9999"))
        guest_motor = self.db.query(models.GuestMotor).filter_by(guest_customer_id=guest.id).first()
        guest_motor.is_new_vehicle = True
        crud.new_vehicle_service.ensure_maintenance_schedule(self.db, guest_motor)
        work_order = models.WorkOrder(
            guest_customer_id=guest.id, guest_motor_id=guest_motor.id,
            vehicle_license_plate=guest_motor.license_plate,
            ordered_date=date.today(), consumption_date=date.today(),
        )
        self.db.add(work_order)
        self.db.commit()

        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))

        self.assertEqual(order.google_id, "member")
        self.assertEqual(work_order.google_id, "member")
        self.assertEqual(work_order.motor_id, motor.id)
        self.assertIsNone(work_order.guest_motor_id)
        self.assertIsNone(work_order.guest_customer_id)
        self.assertEqual(guest_motor.status, "已合併")
        self.assertEqual(self.db.query(models.Motor).count(), 2)
        self.assertTrue(motor.is_new_vehicle)
        self.assertEqual(
            self.db.query(models.NewVehicleMaintenanceRecord).filter_by(motor_id=motor.id).count(),
            len(crud.new_vehicle_service.NEW_VEHICLE_MILESTONES),
        )

    def test_phone_or_plate_merges_all_matches_once(self):
        self.motor()
        _, phone_order = self.guest(phone=self.member.phone)
        _, plate_order = self.guest(plates=("ABC1234", "abc-1234"))
        _, both_order = self.guest(phone=self.member.phone, plates=("abc1234",))
        unrelated, untouched = self.guest(phone="different", plates=("OTHER-1",))

        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))

        for order in (phone_order, plate_order, both_order):
            self.assertEqual(order.google_id, "member")
            self.assertIsNone(order.guest_customer_id)
        self.assertEqual(untouched.guest_customer_id, unrelated.id)
        self.assertIsNone(untouched.google_id)
        self.assertEqual(self.member.cumulative_consumption, 300)
        self.assertEqual(self.db.query(models.Motor).count(), 1)

    def test_blank_plates_and_phones_do_not_match(self):
        self.member.phone = ""
        self.motor(" - \t")
        guest, order = self.guest(phone="", plates=("", " - "))
        crud.update_user(self.db, "member", UserUpdate(phone=""))
        self.assertEqual(order.guest_customer_id, guest.id)
        self.assertIsNone(order.google_id)

    def test_deleted_member_motor_does_not_match(self):
        self.motor(status="已刪除")
        guest, order = self.guest(plates=("ABC1234",))
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        self.assertEqual(order.guest_customer_id, guest.id)

    def test_inactive_guest_motors_do_not_match(self):
        self.motor()
        for status in ("已刪除", "已合併"):
            with self.subTest(status=status):
                guest, order = self.guest(plates=("ABC1234",))
                self.db.query(models.GuestMotor).filter_by(guest_customer_id=guest.id).one().status = status
                self.db.commit()
                crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
                self.assertEqual(order.guest_customer_id, guest.id)

    def test_adding_motor_without_phone_field_triggers_merge(self):
        guest, order = self.guest(plates=("abc1234",))
        crud.update_user(self.db, "member", UserUpdate(motors=[MotorCreate(license_plate="ABC-1234")]))
        self.assertEqual(order.google_id, "member")
        self.assertEqual(self.db.query(models.Motor).count(), 1)

    def test_editing_motor_triggers_merge(self):
        motor = self.motor("OLD-1234")
        guest, order = self.guest(plates=("abc1234",))
        crud.update_motor(self.db, motor.id, MotorUpdate(license_plate="ABC-1234"))
        self.assertEqual(order.google_id, "member")
        self.assertEqual(self.db.query(models.Motor).count(), 1)

    def test_other_member_vehicle_is_not_a_match(self):
        self.db.add(models.User(google_id="other", name="Other", email="other@example.com"))
        self.db.add(models.Motor(google_id="other", license_plate="ABC-1234"))
        self.db.commit()
        guest, order = self.guest(plates=("ABC1234",))
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        self.assertEqual(order.guest_customer_id, guest.id)

    def test_merging_does_not_expand_matches_through_transferred_plates(self):
        self.motor()
        _, matched = self.guest(plates=("ABC1234", "XYZ-9999"))
        unrelated, untouched = self.guest(plates=("XYZ9999",))
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        self.assertEqual(matched.google_id, "member")
        self.assertEqual(untouched.guest_customer_id, unrelated.id)

    def test_unrelated_profile_or_motor_changes_do_not_trigger_merge(self):
        motor = self.motor()
        guest, order = self.guest(phone=self.member.phone, plates=("ABC1234",))
        crud.update_user(self.db, "member", UserUpdate(admin_notes="note"))
        crud.update_motor(self.db, motor.id, MotorUpdate(mileage=500))
        self.assertEqual(order.guest_customer_id, guest.id)

    def test_plate_merge_preserves_paid_work_order_and_awards_consumption_and_points_once(self):
        motor = self.motor()
        guest, order = self.guest(plates=("abc1234",))
        guest_motor = self.db.query(models.GuestMotor).filter_by(guest_customer_id=guest.id).one()
        work_order = models.WorkOrder(
            guest_customer_id=guest.id, guest_motor_id=guest_motor.id,
            ordered_date=date.today(), consumption_date=date.today(),
            status=models.WorkOrderStatus.COMPLETED, total_amount=2000,
            completed_at=datetime.now(), supervisor_reviewed_at=datetime.now(),
            supervisor_reviewed_by="Reviewer",
            line_items=[models.WorkOrderLineItem(
                type="LABOR", name="Service", quantity=1, unit_price=2000,
                counts_toward_membership=True,
            )],
            payments=[models.WorkOrderPayment(amount=2000, method="現金")],
        )
        self.db.add(work_order)
        self.db.commit()
        line_id = work_order.line_items[0].id
        payment_id = work_order.payments[0].id
        reviewed_at = work_order.supervisor_reviewed_at

        crud.update_motor(self.db, motor.id, MotorUpdate(license_plate="ABC-1234"))
        crud.update_user(self.db, "member", UserUpdate(phone=self.member.phone))
        self.db.expire_all()
        self.assertEqual(work_order.google_id, "member")
        self.assertEqual(work_order.motor_id, motor.id)
        self.assertEqual(work_order.total_amount, 2000)
        self.assertEqual(work_order.paid_amount, 2000)
        self.assertEqual(work_order.line_items[0].id, line_id)
        self.assertEqual(work_order.payments[0].id, payment_id)
        self.assertEqual(work_order.supervisor_reviewed_at, reviewed_at)
        self.assertEqual(work_order.status, models.WorkOrderStatus.COMPLETED)
        self.assertEqual(self.member.cumulative_consumption, 2100)
        self.assertEqual(work_order.membership_consumption_amount, 2000)
        points = self.db.query(models.PointTransaction).filter_by(work_order_id=work_order.id).all()
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].points, 2)


if __name__ == "__main__":
    unittest.main()
