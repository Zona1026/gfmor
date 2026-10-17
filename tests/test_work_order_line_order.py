from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import work_orders
from core.config import settings
from db import crud, models
from schemas.work_order import WorkOrder, WorkOrderCreate, WorkOrderLineItemCreate, WorkOrderUpdate
from test_work_order_review_access import ASGIClient


class WorkOrderLineOrderTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.order = models.WorkOrder(
            ordered_date=date.today(), consumption_date=date.today(), total_amount=600,
            line_items=[models.WorkOrderLineItem(type="LABOR", name=name, quantity=1, unit_price=200)
                        for name in ("First", "Second", "Third")],
        )
        self.db.add(self.order)
        self.db.commit()
        self.ids = [item.id for item in self.order.line_items]

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def reload(self):
        self.db.expire_all()
        return crud.get_work_order(self.db, self.order.id)

    def test_order_survives_reload_and_response_serialization(self):
        ids = list(reversed(self.ids))
        crud.reorder_work_order_line_items(self.db, self.order.id, ids)
        loaded = self.reload()
        self.assertEqual([item.id for item in loaded.line_items], ids)
        self.assertEqual([item.sort_order for item in loaded.line_items], [0, 1, 2])
        self.assertEqual([item.id for item in WorkOrder.model_validate(loaded).line_items], ids)

    def test_approved_consumed_lines_keep_ids_inventory_and_purchase_links(self):
        line = self.order.line_items[0]
        product = models.Product(name="Part", price=200, stock=5)
        self.db.add(product)
        self.db.flush()
        line.type = models.WorkOrderLineItemType.PART
        line.product_id = product.id
        line.inventory_deducted = 1
        line.inventory_consumed_quantity = 1
        line.fulfillment_status = "ARRIVED"
        self.order.supervisor_reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.order.supervisor_reviewed_by = "Reviewer"
        self.order.status = models.WorkOrderStatus.COMPLETED
        request = models.PurchaseRequest(
            product_id=product.id, work_order_id=self.order.id,
            work_order_line_item_id=line.id, item_name="Part", requested_quantity=1,
        )
        self.db.add(request)
        self.db.commit()
        reviewed_at = self.order.supervisor_reviewed_at

        crud.reorder_work_order_line_items(self.db, self.order.id, list(reversed(self.ids)))
        order = self.reload()
        self.assertEqual(order.total_amount, 600)
        self.assertEqual(order.supervisor_reviewed_at, reviewed_at)
        self.assertEqual(order.supervisor_reviewed_by, "Reviewer")
        self.assertEqual(order.status, models.WorkOrderStatus.COMPLETED)
        self.assertEqual(request.work_order_line_item_id, line.id)
        self.assertEqual(line.inventory_consumed_quantity, 1)
        self.assertEqual(line.inventory_deducted, 1)
        self.assertEqual(line.fulfillment_status, "ARRIVED")
        self.assertEqual(product.stock, 5)
        self.assertEqual(self.db.query(models.WorkOrderLineItem).count(), 3)
        self.assertEqual(self.db.query(models.PointTransaction).count(), 0)

    def test_rejects_missing_duplicate_unknown_and_foreign_ids_without_partial_changes(self):
        other = models.WorkOrder(
            ordered_date=date.today(), consumption_date=date.today(),
            line_items=[models.WorkOrderLineItem(type="LABOR", name="Other")],
        )
        self.db.add(other)
        self.db.commit()
        invalid_orders = [self.ids[:-1], self.ids + [999], [self.ids[0]] * 3,
                          [*self.ids[:2], other.line_items[0].id], []]
        for ids in invalid_orders:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                crud.reorder_work_order_line_items(self.db, self.order.id, ids)
            self.assertEqual([item.id for item in self.reload().line_items], self.ids)

    def test_deleted_order_rejects_reordering_and_missing_order_returns_none(self):
        self.order.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        with self.assertRaises(ValueError):
            crud.reorder_work_order_line_items(self.db, self.order.id, self.ids)
        self.assertIsNone(crud.reorder_work_order_line_items(self.db, 999, []))

    def test_create_and_update_preserve_submitted_array_order(self):
        order = crud.create_work_order(self.db, WorkOrderCreate(
            guest_name="Guest", guest_phone="Other", vehicle_license_plate="TEST-123",
            vehicle_model="Model", vehicle_mileage=0, responsible_staff="Tester",
            line_items=[WorkOrderLineItemCreate(type="LABOR", name=name, unit_price=200)
                        for name in ("Z", "A", "M")],
        ))
        self.db.expire_all()
        order = crud.get_work_order(self.db, order.id)
        self.assertEqual([item.name for item in order.line_items], ["Z", "A", "M"])
        self.assertEqual([item.sort_order for item in order.line_items], [0, 1, 2])
        data = [{"id": item.id, "type": item.type, "name": item.name, "unit_price": item.unit_price}
                for item in reversed(order.line_items)]
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=data))
        self.db.expire_all()
        self.assertEqual([item.name for item in crud.get_work_order(self.db, order.id).line_items], ["M", "A", "Z"])

    def test_appended_line_goes_after_reordered_lines(self):
        crud.reorder_work_order_line_items(self.db, self.order.id, list(reversed(self.ids)))
        crud.add_work_order_line_item(self.db, self.order.id, WorkOrderLineItemCreate(type="LABOR", name="New"))
        self.assertEqual([item.name for item in self.reload().line_items], ["Third", "Second", "First", "New"])

    def test_gift_keeps_submitted_position_when_rebuilt(self):
        gift = models.WorkOrderLineItem(type="PART", name="Gift", promotion_gift_id=10, product_id=20)
        self.order.line_items.append(gift)
        crud._assign_line_item_order(self.order, [
            {"promotion_gift_id": 10, "product_id": 20}, {}, {}, {},
        ])
        self.assertIs(self.order.line_items[0], gift)
        self.assertEqual([item.sort_order for item in self.order.line_items], [0, 1, 2, 3])

    def test_api_checks_auth_and_rejects_stale_lists(self):
        app = FastAPI()
        app.include_router(work_orders.router, prefix="/work-orders")
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        client = ASGIClient(app)
        url = f"/work-orders/{self.order.id}/line-items/order"
        body = {"line_item_ids": list(reversed(self.ids))}
        self.assertEqual(client.request("PUT", url, json=body).status_code, 401)
        token = jwt.encode({"sub": "staff", "role": "admin", "admin_role": "一般",
                            "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                           settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(client.request("PUT", url, json=body, headers=headers).status_code, 200)
        self.assertEqual([item.id for item in self.reload().line_items], body["line_item_ids"])
        self.assertEqual(client.request("PUT", url, json={"line_item_ids": self.ids[:1]}, headers=headers).status_code, 400)
        self.assertEqual(client.request("PUT", "/work-orders/999/line-items/order", json=body, headers=headers).status_code, 404)

    def test_migration_preserves_legacy_rows_and_can_be_reversed(self):
        path = Path(__file__).parents[1] / "migrations/versions/20261017_0027_work_order_line_order.py"
        spec = importlib.util.spec_from_file_location("line_order_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE work_order_line_items (id INTEGER PRIMARY KEY)"))
                connection.execute(text("INSERT INTO work_order_line_items (id) VALUES (1), (2)"))
                with patch.object(migration, "op", Operations(MigrationContext.configure(connection))):
                    migration.upgrade()
                    self.assertEqual(connection.execute(text("SELECT id, sort_order FROM work_order_line_items ORDER BY sort_order, id")).all(), [(1, 0), (2, 0)])
                    migration.downgrade()
                self.assertEqual(connection.execute(text("SELECT * FROM work_order_line_items")).all(), [(1,), (2,)])
        finally:
            engine.dispose()
