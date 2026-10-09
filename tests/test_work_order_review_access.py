import asyncio
import json
import unittest
from types import SimpleNamespace
from urllib.parse import urlsplit
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.endpoints import work_orders
from core.config import settings
from db import crud, models
from db.database import Base


class ASGIClient:
    """Exercise the real FastAPI authorization path without a test HTTP dependency."""
    def __init__(self, app):
        self.app = app

    def get(self, url, headers=None):
        return self.request("GET", url, headers=headers)

    def request(self, method, url, *, headers=None, json=None):
        from json import dumps
        parsed = urlsplit(url)
        body = dumps(json).encode() if json is not None else b""
        messages = []
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
                 "method": method, "scheme": "http", "path": parsed.path,
                 "raw_path": parsed.path.encode(), "query_string": parsed.query.encode(),
                 "root_path": "", "client": ("127.0.0.1", 1), "server": ("test", 80),
                 "headers": [(k.lower().encode(), v.encode()) for k, v in
                             {"content-type": "application/json", **(headers or {})}.items()]}

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(self.app(scope, receive, send))
        start = next(message for message in messages if message["type"] == "http.response.start")
        return SimpleNamespace(status_code=start["status"])


class WorkOrderReviewAccessTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(work_orders.router, prefix="/work-orders")
        self.db = MagicMock()
        app.dependency_overrides[work_orders.get_db] = lambda: self.db
        self.client = ASGIClient(app)

    def headers(self, role, *, signing_key=None, token_role="admin"):
        token = jwt.encode(
            {"sub": "review-test", "role": token_role, "admin_role": role,
             "exp": datetime.utcnow() + timedelta(minutes=5)},
            signing_key or settings.SECRET_KEY, algorithm=settings.ALGORITHM,
        )
        return {"Authorization": f"Bearer {token}"}

    def test_review_reads_reject_anonymous_staff_and_manager(self):
        for endpoint in ("/work-orders/reviews/", "/work-orders/reviews/1", "/work-orders/approvals/"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 401)
                for role in ("一般", "管理層"):
                    self.assertEqual(self.client.get(endpoint, headers=self.headers(role)).status_code, 403)
        self.db.query.assert_not_called()

    def test_forged_super_token_is_rejected(self):
        response = self.client.get("/work-orders/reviews/", headers=self.headers("最高級", signing_key="forged-key"))
        self.assertEqual(response.status_code, 401)
        self.db.query.assert_not_called()

    def test_member_token_cannot_claim_admin_review_role(self):
        response = self.client.get("/work-orders/reviews/", headers=self.headers("最高級", token_role="member"))
        self.assertEqual(response.status_code, 401)

    def test_super_admin_can_load_queue_and_pagination_is_validated(self):
        with patch("api.endpoints.work_orders.crud.get_work_orders", return_value=[]) as load:
            response = self.client.get("/work-orders/reviews/?q=ABC&skip=50&limit=50", headers=self.headers("最高級"))
        self.assertEqual(response.status_code, 200)
        load.assert_called_once_with(self.db, skip=50, limit=50, q="ABC", review_pending=True)
        self.assertEqual(self.client.get("/work-orders/reviews/?limit=201", headers=self.headers("最高級")).status_code, 422)

    def test_review_detail_missing_record_returns_404(self):
        with patch("api.endpoints.work_orders.crud.get_work_order", return_value=None):
            self.assertEqual(self.client.get("/work-orders/reviews/99", headers=self.headers("最高級")).status_code, 404)

    def test_review_mutations_reject_lower_roles(self):
        calls = (
            ("POST", "/work-orders/1/confirm-review", {}),
            ("PUT", "/work-orders/1/line-items/1/fulfillment-status", {"status": "RESERVED"}),
            ("POST", "/work-orders/approvals/1/approve", {}),
            ("POST", "/work-orders/approvals/1/reject", {"note": "退回"}),
        )
        for method, endpoint, payload in calls:
            for role in ("一般", "管理層"):
                with self.subTest(endpoint=endpoint, role=role):
                    response = self.client.request(method, endpoint, json=payload, headers=self.headers(role))
                    self.assertEqual(response.status_code, 403)
        self.db.query.assert_not_called()


class WorkOrderReviewQueueTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def order(self, *, reviewed=False, pending=False, lines=True, **kwargs):
        order = models.WorkOrder(ordered_date=date.today(), consumption_date=date.today(),
            vehicle_license_plate="TEST", supervisor_reviewed_at=datetime.utcnow() if reviewed else None, **kwargs)
        if lines:
            order.line_items = [models.WorkOrderLineItem(type=models.WorkOrderLineItemType.LABOR,
                name="test labor", quantity=1, unit_price=100)]
        if pending:
            order.approvals = [models.WorkOrderApproval(type=models.WorkOrderApprovalType.DISCOUNT,
                status=models.WorkOrderApprovalStatus.PENDING, title="test approval")]
        self.db.add(order)
        self.db.commit()
        return order

    def test_queue_includes_new_reopened_and_later_pending_approvals(self):
        new = self.order()
        reopened = self.order(status=models.WorkOrderStatus.SUPERVISOR_APPROVAL_PENDING)
        later = self.order(reviewed=True, pending=True)
        self.order(reviewed=True)
        self.order(lines=False)
        self.order(is_historical_backfill=True)
        self.order(status=models.WorkOrderStatus.COMPLETED)
        self.order(status=models.WorkOrderStatus.CANCELED, pending=True)
        self.order(deleted_at=datetime.utcnow(), pending=True)
        ids = {order.id for order in crud.get_work_orders(self.db, review_pending=True, limit=200)}
        self.assertEqual(ids, {new.id, reopened.id, later.id})

    def test_confirmation_removes_order_and_handles_later_approvals(self):
        order = self.order(reviewed=True, pending=True)
        result = crud.confirm_work_order_supervisor_review(self.db, order.id, reviewed_by="review-test")
        self.assertEqual(result.approvals[0].status, models.WorkOrderApprovalStatus.APPROVED)
        self.assertEqual(crud.get_work_orders(self.db, review_pending=True), [])
        repeated = crud.confirm_work_order_supervisor_review(self.db, order.id, reviewed_by="another-reviewer")
        self.assertEqual(repeated.supervisor_reviewed_by, "review-test")


if __name__ == "__main__":
    unittest.main()
