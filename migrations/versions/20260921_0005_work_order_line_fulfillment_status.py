"""Add fulfillment status tracking to work order line items."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260921_0005"
down_revision = "20260920_0004"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    if table_name not in set(inspect(conn).get_table_names()):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_order_line_items")
    with op.batch_alter_table("work_order_line_items") as batch_op:
        if "fulfillment_status" not in columns:
            batch_op.add_column(sa.Column("fulfillment_status", sa.String(length=20), nullable=True))
        if "fulfillment_status_updated_at" not in columns:
            batch_op.add_column(sa.Column("fulfillment_status_updated_at", sa.DateTime(), nullable=True))


def downgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_order_line_items")
    with op.batch_alter_table("work_order_line_items") as batch_op:
        if "fulfillment_status_updated_at" in columns:
            batch_op.drop_column("fulfillment_status_updated_at")
        if "fulfillment_status" in columns:
            batch_op.drop_column("fulfillment_status")
