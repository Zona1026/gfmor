from datetime import date
import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from db import crud, models
from schemas.work_order import WorkOrderUpdate


class ReviewedWorkOrderStockTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.product = models.Product(name="Missing tire", stock=0, price=2800, inventory_type="PART")
        self.order = models.WorkOrder(
            ordered_date=date.today(), consumption_date=date.today(), total_amount=2800,
            status=models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING,
            line_items=[models.WorkOrderLineItem(
                type="PART", name="Missing tire", product=self.product, quantity=1,
                unit_price=2800, is_confirmed=1, fulfillment_status="RESERVED",
            )],
            payments=[models.WorkOrderPayment(amount=2800)],
        )
        self.db.add(self.order)
        self.db.commit()
        crud._request_inventory_reservation_approval(self.order)
        self.db.commit()
        crud.confirm_work_order_supervisor_review(self.db, self.order.id, reviewed_by="Reviewer")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_review_and_manual_reserved_label_do_not_bypass_missing_stock(self):
        with self.assertRaises(ValueError) as raised:
            crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(status="COMPLETED"))
        message = str(raised.exception)
        self.assertIn("Missing tire", message)
        self.assertIn("到貨入庫並分配", message)
        self.assertIn("手動狀態", message)
        self.db.rollback()
        self.assertEqual(self.order.status, models.WorkOrderStatus.IN_PROGRESS)
        self.assertIsNone(self.order.completed_at)
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(self.order.line_items[0].inventory_consumed_quantity, 0)
        self.assertEqual(self.db.query(models.InventoryMovement).count(), 0)
        self.assertEqual(self.db.query(models.PurchaseRequest).count(), 1)

    def test_completion_after_stock_receipt_and_real_allocation_consumes_once(self):
        self.product.stock = 1
        self.db.flush()
        crud._reserve_work_order_inventory(self.db, self.order, actor="Reviewer")
        self.db.commit()
        result = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(status="COMPLETED"))
        self.assertEqual(result.status, models.WorkOrderStatus.COMPLETED)
        self.assertEqual(result.line_items[0].inventory_consumed_quantity, 1)
        self.assertEqual(self.product.stock, 0)
        self.assertIsNotNone(result.completed_at)
        crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(status="COMPLETED"))
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(self.db.query(models.InventoryMovement).count(), 1)


class GuestArchiveMigrationTest(unittest.TestCase):
    def test_legacy_backfill_preserves_unmerged_and_partially_merged_guests(self):
        path = Path(__file__).parents[1] / "migrations/versions/20261023_0032_guest_merge_archive.py"
        spec = importlib.util.spec_from_file_location("guest_archive_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            for statement in [
                'CREATE TABLE users ("Google ID" VARCHAR(255) PRIMARY KEY)',
                'CREATE TABLE guest_customers (id INTEGER PRIMARY KEY, updated_at DATETIME NOT NULL)',
                'CREATE TABLE guest_motors (id INTEGER PRIMARY KEY, guest_customer_id INTEGER, status VARCHAR(50))',
                'CREATE TABLE work_orders (id INTEGER PRIMARY KEY, guest_customer_id INTEGER)',
                'CREATE TABLE orders (id INTEGER PRIMARY KEY, guest_customer_id INTEGER)',
            ]:
                conn.execute(text(statement))
            for guest_id in range(1, 6):
                conn.execute(text("INSERT INTO guest_customers VALUES (:id, '2026-10-23 00:00:00')"), {"id": guest_id})
            conn.execute(text("INSERT INTO guest_motors VALUES (1,1,'已合併'),(2,2,'已合併'),(3,2,NULL),(4,3,'已合併'),(5,4,'已合併')"))
            conn.execute(text("INSERT INTO work_orders VALUES (1,3)"))
            conn.execute(text("INSERT INTO orders VALUES (1,4)"))
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            archived = conn.execute(text("SELECT id FROM guest_customers WHERE merged_at IS NOT NULL")).scalars().all()
            self.assertEqual(archived, [1])
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM guest_customers")).scalar(), 5)
            self.assertIsNone(conn.execute(text("SELECT merged_into_google_id FROM guest_customers WHERE id=1")).scalar())
            with Operations.context(MigrationContext.configure(conn)):
                migration.downgrade()
            self.assertNotIn("merged_at", [c["name"] for c in inspect(conn).get_columns("guest_customers")])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
