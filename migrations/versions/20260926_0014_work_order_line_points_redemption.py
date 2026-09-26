"""Add point redemption to work order line items."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260926_0014"
down_revision = "20260926_0013"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    if "points_redeemed" not in _columns(conn, "work_order_line_items"):
        op.add_column(
            "work_order_line_items",
            sa.Column("points_redeemed", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade():
    conn = op.get_bind()
    if "points_redeemed" in _columns(conn, "work_order_line_items"):
        op.drop_column("work_order_line_items", "points_redeemed")
