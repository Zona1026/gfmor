"""Support one-time substitute purchase receipts without inventory products."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260925_0011"
down_revision = "20260925_0010"
branch_labels = None
depends_on = None


def _columns(conn):
    return {column["name"] for column in inspect(conn).get_columns("purchase_receipts")}


def upgrade():
    conn = op.get_bind()
    columns = _columns(conn)
    if "is_one_time_substitute" not in columns:
        op.add_column(
            "purchase_receipts",
            sa.Column("is_one_time_substitute", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "received_item_name" not in columns:
        op.add_column("purchase_receipts", sa.Column("received_item_name", sa.String(length=100), nullable=True))
    if "unit_cost" not in columns:
        op.add_column("purchase_receipts", sa.Column("unit_cost", sa.Integer(), nullable=True))
    if "replacement_unit_price" not in columns:
        op.add_column("purchase_receipts", sa.Column("replacement_unit_price", sa.Integer(), nullable=True))


def downgrade():
    conn = op.get_bind()
    columns = _columns(conn)
    for column_name in ("replacement_unit_price", "unit_cost", "received_item_name", "is_one_time_substitute"):
        if column_name in columns:
            op.drop_column("purchase_receipts", column_name)
