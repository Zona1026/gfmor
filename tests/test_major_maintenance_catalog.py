import unittest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.endpoints import inventory, products
from db import crud, models
from schemas.work_order import WorkOrderCreate, WorkOrderLineItemCreate, WorkOrderUpdate
from test_product_pricing_fields import ASGIClient


class MajorMaintenanceCatalogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.product = models.Product(name="Major service", price=3000, stock=0, inventory_type="MAJOR_MAINTENANCE")
        self.db.add(self.product)
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

    def line(self, **kwargs):
        return WorkOrderLineItemCreate(type="MAJOR_MAINTENANCE", product_id=self.product.id, name="Major service", **kwargs)

    def create_order(self):
        return crud.create_work_order(self.db, WorkOrderCreate(
            guest_name="Guest", guest_phone="123", vehicle_license_plate="MAJ-123", vehicle_model="Model",
            vehicle_mileage=0, responsible_staff="Tester", line_items=[self.line(quantity=2)],
        ))

    def payload(self, order, **kwargs):
        line = order.line_items[0]
        return {"id": line.id, "type": line.type, "product_id": line.product_id, "name": line.name,
                "unit_price": line.unit_price, "quantity": line.quantity, **kwargs}

    def test_catalog_price_and_type_are_used(self):
        line = crud._build_line_item(self.db, self.line())
        self.assertEqual(line.unit_price, 3000)
        self.assertEqual(line.type, models.WorkOrderLineItemType.MAJOR_MAINTENANCE)
        for price in (0, 2999, 4000):
            with self.subTest(price=price), self.assertRaises(ValueError):
                crud._build_line_item(self.db, self.line(unit_price=price))

    def test_missing_product_or_wrong_type_rejected(self):
        with self.assertRaises(ValueError):
            crud._build_line_item(self.db, WorkOrderLineItemCreate(type="MAJOR_MAINTENANCE", name="Missing"))
        for line_type in ("PART", "LABOR", "DISCOUNT", "SERVICE"):
            with self.subTest(line_type=line_type), self.assertRaises(ValueError):
                crud._build_line_item(self.db, WorkOrderLineItemCreate(type=line_type, product_id=self.product.id, name="Wrong"))

    def test_work_order_price_cannot_be_changed_on_update(self):
        order = self.create_order()
        self.assertEqual(order.total_amount, 6000)
        with self.assertRaises(ValueError):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[self.payload(order, unit_price=1)]))
        self.db.rollback()
        self.assertEqual(crud.get_work_order(self.db, order.id).total_amount, 6000)

    def test_catalog_price_change_applies_to_new_quotes_preserves_existing_quotes(self):
        order = self.create_order()
        result = self.client.request("PUT", f"/products/{self.product.id}", data={"price": 3500})
        self.assertEqual(result.status_code, 200, result.data)
        crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[self.payload(order, quantity=3)]))
        self.db.expire_all()
        order = crud.get_work_order(self.db, order.id)
        self.assertEqual(order.line_items[0].unit_price, 3000)
        self.assertEqual(order.total_amount, 9000)
        self.assertEqual(crud._build_line_item(self.db, self.line()).unit_price, 3500)
        crud._reserve_work_order_inventory(self.db, order)
        for model in (models.InventoryReservation, models.InventoryMovement, models.PurchaseRequest):
            self.assertEqual(self.db.query(model).count(), 0)

    def test_revision_cannot_bypass_price_lock(self):
        order = self.create_order()
        order.revisions.append(models.WorkOrderRevision(reason="Change", previous_status="IN_PROGRESS",
                               previous_snapshot="{}", previous_total_amount=6000, previous_paid_amount=0))
        self.db.commit()
        with self.assertRaises(ValueError):
            crud.update_work_order(self.db, order.id, WorkOrderUpdate(line_items=[self.payload(order, unit_price=1)]))
        self.db.rollback()
        self.assertEqual(crud.get_work_order(self.db, order.id).total_amount, 6000)

    def test_inventory_catalog_create_and_visibility(self):
        response = self.client.request("POST", "/products/", data={"name": "Package", "price": 0, "inventory_type": "MAJOR_MAINTENANCE"})
        self.assertEqual(response.status_code, 200, response.data)
        items = self.client.request("GET", "/inventory/items?type=major_maintenance")
        self.assertEqual(len(items.data), 2)
        self.assertTrue(all(not item["is_low_stock"] for item in items.data))
        for query in ("type=shop", "type=part", "type=all&low_stock=true"):
            rows = self.client.request("GET", "/inventory/items?" + query)
            self.assertNotIn(self.product.id, [row["id"] for row in rows.data])
        self.assertNotIn(self.product.id, [p.id for p in crud.get_products(self.db)])
