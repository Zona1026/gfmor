from datetime import date, datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import crud, models
from schemas.work_order import WorkOrder, WorkOrderPaymentCreate, WorkOrderUpdate


class ZeroTotalWorkOrderPaymentTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def order(self, total=0, paid=0, refunded=0, **values):
        order = models.WorkOrder(
            ordered_date=date.today(), consumption_date=date.today(),
            total_amount=total, payment_status=models.WorkOrderPaymentStatus.UNPAID,
            **values,
        )
        if paid:
            order.payments = [models.WorkOrderPayment(amount=paid, method="Cash")]
        if refunded:
            order.refund_records = [models.RefundRecord(
                source_type="WORK_ORDER", source_id=1, amount=refunded,
                method="Cash", reason="Refund",
            )]
        return order

    def test_zero_total_needs_no_payment_record(self):
        order = self.order(status=models.WorkOrderStatus.COMPLETED)
        crud._sync_payment_status(order)
        self.assertEqual(order.payment_status, models.WorkOrderPaymentStatus.PAID)
        self.assertEqual(order.balance_amount, 0)
        self.assertEqual(order.payments, [])

    def test_existing_discounted_completed_order_is_fixed_on_save(self):
        order = self.order(id=132, status=models.WorkOrderStatus.COMPLETED)
        order.line_items = [
            models.WorkOrderLineItem(type="LABOR", name="Service", quantity=1, unit_price=100),
            models.WorkOrderLineItem(type="DISCOUNT", name="Discount", quantity=1, unit_price=100),
        ]
        self.db.add(order)
        self.db.commit()
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(notes="Checked"))
        self.db.expire_all()
        saved = crud.get_work_order(self.db, order.id)
        self.assertEqual(saved.status, models.WorkOrderStatus.COMPLETED)
        self.assertEqual(saved.total_amount, 0)
        self.assertEqual(WorkOrder.model_validate(saved).payment_status, models.WorkOrderPaymentStatus.PAID)
        self.assertEqual(saved.paid_amount, 0)
        self.assertEqual(saved.payments, [])
        self.assertEqual(self.db.query(models.PaymentRecord).count(), 0)

    def test_positive_balances_and_refunds_keep_existing_statuses(self):
        cases = [
            (100, 0, 0, "UNPAID"),
            (100, 40, 0, "PARTIALLY_PAID"),
            (100, 100, 0, "PAID"),
            (100, 150, 0, "PAID"),
            (100, 100, 100, "REFUNDED"),
            (0, 100, 100, "REFUNDED"),
            (100, 100, 40, "PARTIALLY_PAID"),
        ]
        for total, paid, refunded, expected in cases:
            with self.subTest(total=total, paid=paid, refunded=refunded):
                order = self.order(total, paid, refunded)
                crud._sync_payment_status(order)
                self.assertEqual(order.payment_status.value, expected)

    def test_new_balance_reverts_to_unpaid_without_inventing_payments(self):
        order = self.order(status=models.WorkOrderStatus.COMPLETED)
        crud._sync_payment_status(order)
        self.assertEqual(order.payment_status, models.WorkOrderPaymentStatus.PAID)
        order.total_amount = 100
        crud._sync_payment_status(order)
        self.assertEqual(order.payment_status, models.WorkOrderPaymentStatus.UNPAID)
        self.assertEqual(order.payments, [])

    def test_zero_total_other_statuses_keep_original_payment_logic(self):
        for status in [None, *models.WorkOrderStatus]:
            if status == models.WorkOrderStatus.COMPLETED:
                continue
            for paid, refunded, expected in [
                (0, 0, "UNPAID"),
                (100, 0, "PAID"),
                (100, 40, "PAID"),
                (100, 100, "REFUNDED"),
            ]:
                with self.subTest(status=status, paid=paid, refunded=refunded):
                    order = self.order(paid=paid, refunded=refunded, status=status)
                    crud._sync_payment_status(order)
                    self.assertEqual(order.payment_status.value, expected)
                    self.assertEqual(order.status, status)

    def test_completed_zero_total_full_refund_stays_refunded(self):
        order = self.order(paid=100, refunded=100, status=models.WorkOrderStatus.COMPLETED)
        crud._sync_payment_status(order)
        self.assertEqual(order.payment_status, models.WorkOrderPaymentStatus.REFUNDED)

    def test_zero_total_payment_status_tracks_completion_and_reopening(self):
        order = self.order(status=models.WorkOrderStatus.AWAITING_PAYMENT)
        order.line_items = [
            models.WorkOrderLineItem(type="LABOR", name="No charge", quantity=1, unit_price=0),
        ]
        self.db.add(order)
        self.db.commit()
        completed = crud.update_work_order(
            self.db, order.id, WorkOrderUpdate(status=models.WorkOrderStatus.COMPLETED),
        )
        self.assertEqual(completed.payment_status, models.WorkOrderPaymentStatus.PAID)
        reopened = crud.update_work_order(
            self.db, order.id, WorkOrderUpdate(status=models.WorkOrderStatus.AWAITING_PAYMENT),
        )
        self.assertEqual(reopened.payment_status, models.WorkOrderPaymentStatus.UNPAID)
        self.assertEqual(reopened.payments, [])
        self.assertEqual(self.db.query(models.PaymentRecord).count(), 0)

    def test_actual_payment_records_still_require_a_positive_amount(self):
        order = self.order(status="COMPLETED")
        self.db.add(order)
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "付款金額需大於 0"):
            crud.add_work_order_payment(
                self.db, order.id, WorkOrderPaymentCreate(amount=0, method="Cash"),
            )
        self.assertEqual(self.db.query(models.WorkOrderPayment).count(), 0)

    def test_migration_repairs_only_unpaid_zero_total_completed_orders(self):
        orders = [
            self.order(id=132, status="COMPLETED"),
            self.order(total=100, status="COMPLETED"),
            self.order(status="IN_PROGRESS"),
            self.order(status="CANCELED"),
            self.order(status="COMPLETED", deleted_at=datetime.now()),
            self.order(paid=100, status="COMPLETED"),
            self.order(status="COMPLETED"),
        ]
        orders[-1].payment_status = models.WorkOrderPaymentStatus.REFUNDED
        self.db.add_all(orders)
        self.db.commit()
        ids = [order.id for order in orders]
        migration_path = Path(__file__).parents[1] / "migrations/versions/20261115_0033_zero_total_work_order_payment.py"
        spec = importlib.util.spec_from_file_location("zero_total_payment_migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as connection:
            with patch.object(migration, "op", Operations(MigrationContext.configure(connection))):
                migration.upgrade()
                migration.upgrade()
        self.db.expire_all()
        self.assertEqual(
            [self.db.get(models.WorkOrder, order_id).payment_status.value for order_id in ids],
            ["PAID", "UNPAID", "UNPAID", "UNPAID", "UNPAID", "UNPAID", "REFUNDED"],
        )
        self.assertEqual(self.db.query(models.WorkOrderPayment).count(), 1)
        self.assertEqual(self.db.query(models.PaymentRecord).count(), 0)
