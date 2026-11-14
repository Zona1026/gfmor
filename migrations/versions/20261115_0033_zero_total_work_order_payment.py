"""Settle completed zero-total work orders without creating payment records."""
from alembic import op
import sqlalchemy as sa


revision = "20261115_0033"
down_revision = "20261023_0032"
branch_labels = None
depends_on = None


def upgrade():
    # Only repair completed orders with no money movement. Preserve refunds,
    # canceled/deleted orders and unfinished drafts for manual review.
    op.execute(sa.text("""
        UPDATE work_orders SET payment_status = 'PAID'
        WHERE total_amount = 0 AND status = 'COMPLETED'
          AND payment_status = 'UNPAID' AND deleted_at IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM work_order_payments p
              WHERE p.work_order_id = work_orders.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM refund_records r
              WHERE r.work_order_id = work_orders.id
          )
    """))


def downgrade():
    # Keep corrected financial statuses on rollback; no schema was changed.
    pass
