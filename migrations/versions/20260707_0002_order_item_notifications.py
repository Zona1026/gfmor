"""Add order item notification records."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260707_0002"
down_revision = "20260707_0001"
branch_labels = None
depends_on = None


def _tables(conn):
    return set(inspect(conn).get_table_names())


def _indexes(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {index["name"] for index in inspect(conn).get_indexes(table_name)}


def _create_index_if_missing(conn, name, table_name, columns):
    if name not in _indexes(conn, table_name):
        op.create_index(name, table_name, columns)


def upgrade():
    conn = op.get_bind()
    if "order_item_notifications" not in _tables(conn):
        op.create_table(
            "order_item_notifications",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_item_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("method", sa.String(length=50), nullable=False),
            sa.Column("recipient_name", sa.String(length=50), nullable=True),
            sa.Column("recipient_phone", sa.String(length=20), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("actor", sa.String(length=50), nullable=True),
            sa.Column("notified_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"]),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        )

    _create_index_if_missing(conn, "ix_order_item_notifications_id", "order_item_notifications", ["id"])
    _create_index_if_missing(conn, "ix_order_item_notifications_order_item_id", "order_item_notifications", ["order_item_id"])
    _create_index_if_missing(conn, "ix_order_item_notifications_order_id", "order_item_notifications", ["order_id"])


def downgrade():
    # Keep notification history intact on production rollbacks.
    pass
