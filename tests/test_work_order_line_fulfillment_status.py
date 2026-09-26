import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from db import crud
from schemas.work_order import WorkOrderLineItemFulfillmentStatusUpdate


class WorkOrderLineItemFulfillmentStatusTest(unittest.TestCase):
    def test_schema_accepts_all_selectable_statuses(self):
        for status in ("PENDING", "RESERVED", "ORDERED", "ARRIVED"):
            payload = WorkOrderLineItemFulfillmentStatusUpdate(status=status)
            self.assertEqual(payload.status, status)

        with self.assertRaises(ValidationError):
            WorkOrderLineItemFulfillmentStatusUpdate(status="INVALID")

    def test_status_can_be_changed_back_to_pending(self):
        line_item = SimpleNamespace(fulfillment_status="ARRIVED")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = line_item

        with patch("db.crud.get_work_order", return_value="updated-work-order"):
            result = crud.update_work_order_line_item_fulfillment_status(
                db,
                work_order_id=1,
                line_item_id=2,
                fulfillment_status="PENDING",
            )

        self.assertEqual(line_item.fulfillment_status, "PENDING")
        self.assertEqual(result, "updated-work-order")
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
