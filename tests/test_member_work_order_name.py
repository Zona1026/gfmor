from datetime import date
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import crud, models
from schemas.user import UserUpdate
from schemas.work_order import WorkOrder, WorkOrderApprovalWorkOrderSummary


class MemberWorkOrderNameTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        models.Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([
            models.User(google_id='member', name='Nickname', email='member@example.com'),
            models.User(google_id='other', name='Nickname', email='other@example.com'),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def order(self, google_id='member', **kwargs):
        order = models.WorkOrder(
            google_id=google_id, customer_name='Nickname', ordered_date=date.today(),
            consumption_date=date.today(), **kwargs,
        )
        self.db.add(order)
        self.db.commit()
        return order

    def test_rename_syncs_open_and_completed_orders_only_for_this_member(self):
        active = self.order()
        completed = self.order(status=models.WorkOrderStatus.COMPLETED)
        other = self.order('other')
        guest = self.order(None)
        crud.update_user(self.db, 'member', UserUpdate(name='Real Name'))
        self.assertEqual(active.customer_name, 'Real Name')
        self.assertEqual(completed.customer_name, 'Real Name')
        self.assertEqual(other.customer_name, 'Nickname')
        self.assertEqual(guest.customer_name, 'Nickname')

    def test_saving_current_name_repairs_stale_order_names(self):
        order = self.order()
        user = crud.get_user(self.db, 'member')
        user.name = 'Real Name'
        self.db.commit()
        crud.update_user(self.db, 'member', UserUpdate(name='Real Name'))
        self.assertEqual(order.customer_name, 'Real Name')

    def test_update_without_name_leaves_order_name_unchanged(self):
        order = self.order()
        crud.update_user(self.db, 'member', UserUpdate(admin_notes='Updated'))
        self.assertEqual(order.customer_name, 'Nickname')

    def test_existing_stale_order_returns_current_member_name(self):
        order = self.order()
        user = crud.get_user(self.db, 'member')
        user.name = 'Real Name'
        self.db.commit()
        detail = crud.get_work_order(self.db, order.id)
        self.assertEqual(WorkOrder.model_validate(detail).customer_name, 'Real Name')
        self.assertEqual(WorkOrderApprovalWorkOrderSummary.model_validate(detail).customer_name, 'Real Name')
        self.assertEqual(detail.customer_name, 'Nickname')

    def test_search_by_current_member_name_finds_direct_orders(self):
        order = self.order()
        user = crud.get_user(self.db, 'member')
        user.name = 'Real Name'
        self.db.commit()
        results = crud.get_work_orders(self.db, q='Real Name')
        self.assertEqual([result.id for result in results], [order.id])
        self.assertEqual(WorkOrder.model_validate(results[0]).customer_name, 'Real Name')

    def test_guest_response_keeps_recorded_name(self):
        order = self.order(None)
        self.assertEqual(WorkOrder.model_validate(order).customer_name, 'Nickname')
