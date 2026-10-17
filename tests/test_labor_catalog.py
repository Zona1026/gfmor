import importlib.util
from pathlib import Path
import unittest

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import inventory, products
from db import crud, models
from schemas.work_order import WorkOrderCreate, WorkOrderLineItemCreate, WorkOrderUpdate
from test_product_pricing_fields import ASGIClient


class LaborCatalogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.labor = models.Product(name="Service", price=500, stock=0, inventory_type="LABOR")
        self.part = models.Product(name="Part", price=200, stock=10, inventory_type="PART")
        self.db.add_all([self.labor, self.part])
        self.db.commit()
        app = FastAPI()
        app.include_router(products.router, prefix="/products")
        app.include_router(inventory.router, prefix="/inventory")
        app.dependency_overrides[products.get_db] = lambda: self.db
        app.dependency_overrides[products.require_manager_admin] = lambda: {"is_manager": True}
        app.dependency_overrides[inventory.require_admin] = lambda: {"is_manager": True}
        self.client = ASGIClient(app)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_catalog_create_zero_price_edit_and_work_order_options(self):
        created = self.client.request("POST", "/products/", data={"name": "Zero service", "inventory_type": "LABOR", "price": 0})
        self.assertEqual(created.status_code, 200, created.data)
        product_id = created.data["id"]
        items = self.client.request("GET", "/inventory/items?type=labor")
        self.assertEqual({item["id"] for item in items.data}, {self.labor.id, product_id})
        self.assertTrue(all(not item["is_low_stock"] for item in items.data))
        updated = self.client.request("PUT", f"/products/{product_id}", data={"price": 350})
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["price"], 350)
        self.assertEqual(self.client.request("PUT", f"/products/{product_id}", data={"price": -1}).status_code, 422)

    def test_default_and_explicit_zero_or_custom_price(self):
        for supplied, expected in [({}, 500), ({"unit_price": 0}, 0), ({"unit_price": 725}, 725)]:
            line = crud._build_line_item(self.db, WorkOrderLineItemCreate(type="LABOR", name="", product_id=self.labor.id, **supplied))
            self.assertEqual(line.unit_price, expected)
            self.assertEqual(line.name, "Service")
        self.assertEqual(self.labor.price, 500)

    def test_create_update_reload_does_not_change_catalog_or_stock(self):
        order = crud.create_work_order(self.db, WorkOrderCreate(
            guest_name="Guest", guest_phone="123", vehicle_license_plate="LAB-123",
            vehicle_model="Model", vehicle_mileage=0, responsible_staff="Tester",
            line_items=[{"type": "LABOR", "name": "Service", "product_id": self.labor.id, "unit_price": 725, "quantity": 2}],
        ))
        self.assertEqual(order.total_amount, 1450)
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[{
            "id": order.line_items[0].id, "type": "LABOR", "name": "Service",
            "product_id": self.labor.id, "unit_price": 0, "quantity": 2,
        }]))
        self.db.expire_all()
        order = crud.get_work_order(self.db, order.id)
        self.assertEqual(order.line_items[0].product_id, self.labor.id)
        self.assertEqual(order.line_items[0].unit_price, 0)
        self.assertEqual(order.total_amount, 0)
        crud._reserve_work_order_inventory(self.db, order)
        self.assertEqual(self.labor.price, 500)
        self.assertEqual(self.labor.stock, 0)
        for model in (models.InventoryReservation, models.InventoryMovement, models.PurchaseRequest):
            self.assertEqual(self.db.query(model).count(), 0)

    def test_catalog_type_mismatch_is_rejected_and_legacy_labor_still_works(self):
        for line_type, product in [("PART", self.labor), ("LABOR", self.part)]:
            with self.assertRaises(ValueError):
                crud._build_line_item(self.db, WorkOrderLineItemCreate(type=line_type, name="Test", product_id=product.id))
        legacy = crud._build_line_item(self.db, WorkOrderLineItemCreate(type="LABOR", name="Legacy", unit_price=100))
        self.assertIsNone(legacy.product_id)
        self.assertEqual(legacy.unit_price, 100)

    def test_labor_excluded_from_shop_parts_and_low_stock(self):
        for query in ("type=shop", "type=part", "type=all&low_stock=true"):
            response = self.client.request("GET", "/inventory/items?" + query)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(self.labor.id, [item["id"] for item in response.data])
        self.assertNotIn(self.labor.id, [item.id for item in crud.get_products(self.db)])
        page = products.read_paginated_products(page=1, page_size=50, db=self.db)
        self.assertNotIn(self.labor.id, [item.id for item in page["items"]])

    def test_migration_handles_varchar_and_refuses_lossy_downgrade(self):
        path = Path(__file__).parents[1] / "migrations/versions/20261017_0028_labor_catalog.py"
        spec = importlib.util.spec_from_file_location("labor_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
                with self.assertRaises(RuntimeError):
                    migration.downgrade()
