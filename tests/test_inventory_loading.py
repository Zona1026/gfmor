import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from api.endpoints.inventory import read_inventory_items
from db import models
from schemas.inventory import InventoryProduct


class InventoryLoadingTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        category = models.ProductCategory(name='Parts')
        extra = models.ProductExtraCategory(name='Workshop')
        self.products = [models.Product(name=f'Part {i}', stock=10, price=100,
                                       category_info=category,
                                       additional_categories=[category], extra_categories=[extra])
                         for i in range(20)]
        self.db.add_all(self.products)
        self.db.flush()
        self.first_id = self.products[0].id
        self.db.add_all([
            models.InventoryReservation(product_id=self.first_id, quantity=3,
                                        status=models.InventoryReservationStatus.ACTIVE,
                                        source_type='test', source_id=1),
            models.InventoryReservation(product_id=self.first_id, quantity=2,
                                        status=models.InventoryReservationStatus.ACTIVE,
                                        source_type='test', source_id=2),
            models.InventoryReservation(product_id=self.first_id, quantity=7,
                                        status=models.InventoryReservationStatus.RELEASED,
                                        source_type='test', source_id=3),
        ])
        self.db.commit()
        self.db.expunge_all()
        self.selects = []
        event.listen(self.engine, 'before_cursor_execute', self.record_query)

    def record_query(self, conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            self.selects.append(statement)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def load(self, manager=True, low_stock=False):
        return [InventoryProduct.model_validate(item) for item in read_inventory_items(
            type='all', low_stock=low_stock, db=self.db, admin={'is_manager': manager})]

    def test_twenty_products_use_batch_queries_with_correct_stock_and_categories(self):
        items = self.load()
        self.assertEqual(len(items), 20)
        self.assertEqual(len(self.selects), 4)
        first = next(item for item in items if item.id == self.first_id)
        self.assertEqual((first.reserved_stock, first.available_stock), (5, 5))
        self.assertEqual(len(first.categories), 1)
        self.assertEqual(first.extra_categories[0].name, 'Workshop')
        self.assertEqual(items[-1].reserved_stock, 0)

    def test_low_stock_filter_and_staff_visibility_are_preserved(self):
        items = self.load(manager=False, low_stock=True)
        self.assertEqual([item.id for item in items], [self.first_id])
        self.assertIsNone(items[0].stock)
        self.assertIsNone(items[0].reserved_stock)
        self.assertEqual(items[0].available_stock, 5)


if __name__ == '__main__':
    unittest.main()
