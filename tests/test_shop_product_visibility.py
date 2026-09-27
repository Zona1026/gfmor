import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from api.endpoints.orders import create_order
from api.endpoints.products import read_paginated_products
from db import models


class ShopProductVisibilityTest(unittest.TestCase):
    def test_paginated_shop_products_filter_out_part_only_inventory(self):
        query = MagicMock()
        query.filter.return_value = query
        query.count.return_value = 0
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.all.return_value = []
        db = MagicMock()
        db.query.return_value = query

        result = read_paginated_products(
            page=1,
            page_size=50,
            search=None,
            category_id=None,
            uncategorized=False,
            status="active",
            db=db,
        )

        filter_expressions = [str(call.args[0]) for call in query.filter.call_args_list]
        self.assertTrue(any("products.inventory_type IN" in expression for expression in filter_expressions))
        self.assertEqual(result["items"], [])

    def test_online_order_rejects_part_only_inventory(self):
        user_query = MagicMock()
        user_query.filter.return_value.first.return_value = SimpleNamespace(google_id="member-1")
        product_query = MagicMock()
        product_query.get.return_value = SimpleNamespace(
            id=4,
            name="螺絲",
            is_active=1,
            inventory_type=models.InventoryType.PART,
        )
        db = MagicMock()
        db.query.side_effect = lambda model: user_query if model is models.User else product_query
        order_data = SimpleNamespace(
            google_id="member-1",
            items=[SimpleNamespace(product_id=4, quantity=1)],
        )

        with patch("api.endpoints.orders.ensure_self_or_manager"):
            with self.assertRaises(HTTPException) as raised:
                create_order(order_data=order_data, auth={}, db=db)

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("不提供線上販售", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
