from datetime import date, datetime, timedelta
import importlib.util
import json
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import work_orders
from core.config import settings
from db import crud, inventory, models, purchases
from schemas.purchase import PurchaseReceiveCreate, PurchaseRequest
from schemas.work_order import WorkOrderReopenCreate, WorkOrderUpdate
from test_work_order_review_access import ASGIClient


class WorkOrderReopenResetTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        event.listen(self.engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.product = models.Product(name="Part", price=100, stock=10)
        self.replacement = models.Product(name="Replacement", price=50, stock=5)
        self.order = models.WorkOrder(
            ordered_date=date.today(), consumption_date=date.today(),
            status=models.WorkOrderStatus.IN_PROGRESS, total_amount=200,
            supervisor_reviewed_at=datetime(2026, 10, 17), supervisor_reviewed_by="Original reviewer",
            line_items=[models.WorkOrderLineItem(type="PART", name="Part", product=self.product,
                                               quantity=2, unit_price=100, fulfillment_status="ARRIVED")],
            payments=[models.WorkOrderPayment(amount=200, method="Cash")],
        )
        self.db.add_all([self.order, self.replacement])
        self.db.commit()
        self.line = self.order.line_items[0]
        self.request = models.PurchaseRequest(
            product_id=self.product.id, work_order_id=self.order.id, work_order_line_item=self.line,
            item_name="Part", requested_quantity=2, ordered_quantity=2, arrived_quantity=2,
            assigned_quantity=0, status=models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT,
            receipts=[models.PurchaseReceipt(quantity=2, received_product_id=self.product.id)],
        )
        self.db.add(self.request)
        self.db.flush()
        purchases.assign_arrived_quantity(self.db, self.request, self.order, self.line, 2, actor="Receiver")
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def reopen(self):
        return crud.reopen_work_order(self.db, self.order.id, WorkOrderReopenCreate(reason="Customer changed quote"), actor="Super")

    def test_reopen_releases_allocations_and_reservations_preserving_history_and_money(self):
        self.order.approvals.append(models.WorkOrderApproval(
            type="INVENTORY_CONSUMPTION", title="Old consumption request", status="PENDING"))
        self.db.commit()
        order = self.reopen()
        self.db.expire_all()
        self.assertEqual(order.status, models.WorkOrderStatus.QUOTE_PENDING)
        self.assertIsNone(order.supervisor_reviewed_at)
        self.assertIsNone(order.supervisor_reviewed_by)
        self.assertEqual(self.request.assigned_quantity, 0)
        self.assertEqual(self.request.unassigned_arrived_quantity, 2)
        self.assertEqual(self.request.status, models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT)
        self.assertIsNone(self.request.work_order_line_item_id)
        self.assertEqual((self.request.ordered_quantity, self.request.arrived_quantity), (2, 2))
        self.assertEqual(len(self.request.receipts), 1)
        self.assertEqual(sorted(a.quantity for a in self.request.assignments), [-2, 2])
        self.assertEqual(self.line.inventory_reserved_quantity, 0)
        self.assertEqual(inventory.available_stock(self.db, self.product), 10)
        self.assertEqual(self.product.stock, 10)
        self.assertIsNone(self.line.fulfillment_status)
        self.assertEqual(order.paid_amount, 200)
        self.assertEqual(order.total_amount, 200)
        snapshot = json.loads(order.revisions[0].previous_snapshot)
        self.assertEqual(snapshot["supervisor_reviewed_by"], "Original reviewer")
        self.assertEqual(snapshot["line_items"][0]["product_id"], self.product.id)
        self.assertFalse(any(a.type == models.WorkOrderApprovalType.INVENTORY_CONSUMPTION
                             and a.status == models.WorkOrderApprovalStatus.PENDING for a in order.approvals))
        crud.confirm_work_order_supervisor_review(self.db, order.id, reviewed_by="Super")
        self.assertEqual(self.line.inventory_consumed_quantity, 0)
        self.assertEqual(self.product.stock, 10)
        self.assertIsNotNone(order.revisions[0].closed_at)

    def test_reopened_lines_can_be_replaced_added_removed_and_refund_is_recalculated(self):
        self.reopen()
        old_id = self.line.id
        order = crud.update_work_order(self.db, self.order.id, WorkOrderUpdate(line_items=[
            {"id": old_id, "type": "PART", "name": "Replacement", "product_id": self.replacement.id,
             "quantity": 1, "unit_price": 50},
            {"type": "LABOR", "name": "New labor", "unit_price": 30},
        ]))
        self.assertEqual(order.line_items[0].id, old_id)
        self.assertEqual(order.line_items[0].product_id, self.replacement.id)
        self.assertEqual(order.total_amount, 80)
        self.assertEqual(order.revisions[0].refund_due_amount, 120)
        self.assertEqual(order.revisions[0].refund_status, "PENDING")
        order = crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[
            {"type": "LABOR", "name": "Final labor", "unit_price": 20},
        ]))
        self.db.expire_all()
        self.assertEqual([line.name for line in order.line_items], ["Final labor"])
        self.assertEqual(len(self.request.assignments), 2)
        self.assertTrue(all(a.work_order_line_item_id is None for a in self.request.assignments))
        self.assertEqual(len(PurchaseRequest.model_validate(self.request).assignments), 2)
        self.assertEqual(order.paid_amount, 200)
        self.assertEqual(order.revisions[0].refund_due_amount, 180)
        self.assertEqual(self.product.stock, 10)

    def test_allocations_to_other_work_orders_are_preserved(self):
        other = models.WorkOrder(ordered_date=date.today(), consumption_date=date.today(),
                                 line_items=[models.WorkOrderLineItem(type="PART", name="Part", product=self.product,
                                                                    quantity=1, unit_price=100)])
        self.db.add(other)
        self.db.flush()
        self.request.requested_quantity = 3
        self.request.ordered_quantity = 3
        self.request.arrived_quantity = 3
        purchases.assign_arrived_quantity(self.db, self.request, other, other.line_items[0], 1)
        self.db.commit()
        self.reopen()
        self.assertEqual(self.request.assigned_quantity, 1)
        self.assertEqual(other.line_items[0].inventory_reserved_quantity, 1)
        self.assertEqual(inventory.reserved_quantity(self.db, self.product.id), 1)
        self.assertEqual(sum(a.quantity for a in self.request.assignments if a.work_order_id == other.id), 1)

    def test_allocations_from_another_source_request_are_released(self):
        self.request.work_order_id = None
        self.request.work_order_line_item = None
        self.db.commit()
        self.reopen()
        self.assertEqual(self.request.assigned_quantity, 0)
        self.assertEqual(self.request.status, models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT)
        self.assertEqual(self.line.inventory_reserved_quantity, 0)

    def test_repeated_reopen_does_not_release_more_than_the_new_allocation(self):
        self.reopen()
        crud.confirm_work_order_supervisor_review(self.db, self.order.id, reviewed_by="Super")
        self.reopen()
        self.assertEqual(sorted(a.quantity for a in self.request.assignments), [-2, 2])
        self.assertEqual(self.request.assigned_quantity, 0)
        self.assertEqual(self.product.stock, 10)

    def test_ordered_purchase_is_preserved_and_late_arrival_does_not_reallocate(self):
        later = models.PurchaseRequest(
            product_id=self.product.id, work_order_id=self.order.id, work_order_line_item=self.line,
            item_name="Part", requested_quantity=1, ordered_quantity=1, arrived_quantity=0,
            assigned_quantity=0, status=models.PurchaseRequestStatus.ORDERED,
        )
        self.db.add(later)
        self.db.commit()
        self.reopen()
        self.assertEqual(later.status, models.PurchaseRequestStatus.ORDERED)
        self.assertIsNone(later.work_order_line_item_id)
        purchases.receive_purchase_request(self.db, later, PurchaseReceiveCreate(quantity=1))
        self.db.commit()
        self.assertEqual(later.status, models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT)
        self.assertEqual(later.assigned_quantity, 0)
        self.assertEqual(self.line.inventory_reserved_quantity, 0)
        self.assertEqual(self.product.stock, 11)

    def test_new_allocation_after_review_can_be_released_again(self):
        self.reopen()
        crud.confirm_work_order_supervisor_review(self.db, self.order.id, reviewed_by="Super")
        inventory.release_work_order_line_item(self.db, self.line)
        self.db.commit()
        purchases.assign_arrived_quantity(self.db, self.request, self.order, self.line, 2)
        self.db.commit()
        self.reopen()
        self.assertEqual(sorted(a.quantity for a in self.request.assignments), [-2, -2, 2, 2])
        self.assertEqual(self.request.assigned_quantity, 0)
        self.assertEqual(self.line.inventory_reserved_quantity, 0)

    def test_legacy_assigned_quantities_without_ledger_can_be_released(self):
        self.db.query(models.PurchaseAssignment).delete()
        self.db.commit()
        self.reopen()
        self.assertEqual(self.request.assigned_quantity, 0)
        self.assertEqual(sum(a.quantity for a in self.request.assignments), 0)

    def test_consumed_orders_and_blank_reason_do_not_change_allocations(self):
        with self.assertRaises(ValueError):
            crud.reopen_work_order(self.db, self.order.id, WorkOrderReopenCreate(reason=" "), actor="Super")
        self.assertEqual(self.request.assigned_quantity, 2)
        self.line.inventory_consumed_quantity = 1
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "實際扣庫存"):
            self.reopen()
        self.assertEqual(self.request.assigned_quantity, 2)
        self.assertEqual(self.db.query(models.WorkOrderRevision).count(), 0)

    def test_api_only_super_admin_can_reopen_assigned_order(self):
        app = FastAPI()
        app.include_router(work_orders.router, prefix="/work-orders")
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        client = ASGIClient(app)
        url = f"/work-orders/{self.order.id}/reopen"
        for role, status in (("一般", 403), ("管理層", 403), ("最高級", 200)):
            token = jwt.encode({"sub": "Super", "role": "admin", "admin_role": role,
                                "exp": datetime.utcnow() + timedelta(minutes=5)}, settings.SECRET_KEY,
                               algorithm=settings.ALGORITHM)
            response = client.request("POST", url, headers={"Authorization": f"Bearer {token}"}, json={"reason": "Change"})
            self.assertEqual(response.status_code, status)

    def test_migration_retains_existing_assignment_rows(self):
        path = Path(__file__).parents[1] / "migrations/versions/20261017_0030_purchase_assignment_history.py"
        spec = importlib.util.spec_from_file_location("assignment_history_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE purchase_assignments (id INTEGER PRIMARY KEY, work_order_line_item_id INTEGER NOT NULL)"))
            connection.execute(text("INSERT INTO purchase_assignments VALUES (1, 10)"))
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                self.assertTrue(inspect(connection).get_columns("purchase_assignments")[1]["nullable"])
                self.assertEqual(connection.execute(text("SELECT work_order_line_item_id FROM purchase_assignments")).scalar(), 10)
                migration.downgrade()
                self.assertFalse(inspect(connection).get_columns("purchase_assignments")[1]["nullable"])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
