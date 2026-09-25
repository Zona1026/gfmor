"""Add work order refund type and inventory action."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260925_0012"
down_revision = "20260925_0011"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    columns = _columns(conn, "refund_records")
    if "refund_type" not in columns:
        op.add_column(
            "refund_records",
            sa.Column("refund_type", sa.String(length=30), nullable=False, server_default="PARTIAL"),
        )
    if "inventory_action" not in columns:
        op.add_column(
            "refund_records",
            sa.Column("inventory_action", sa.String(length=30), nullable=False, server_default="NO_CHANGE"),
        )


def downgrade():
    conn = op.get_bind()
    columns = _columns(conn, "refund_records")
    if "inventory_action" in columns:
        op.drop_column("refund_records", "inventory_action")
    if "refund_type" in columns:
        op.drop_column("refund_records", "refund_type")
