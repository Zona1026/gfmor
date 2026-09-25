"""Add auditable work order revisions and substitute purchase receipts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260925_0009"
down_revision = "20260925_0008"
branch_labels = None
depends_on = None


def _tables(conn):
    return set(inspect(conn).get_table_names())


def _columns(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    receipt_columns = _columns(conn, "purchase_receipts")
    if "received_product_id" not in receipt_columns:
        op.add_column("purchase_receipts", sa.Column("received_product_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_purchase_receipts_received_product_id",
            "purchase_receipts",
            "products",
            ["received_product_id"],
            ["id"],
        )
        op.create_index(
            "ix_purchase_receipts_received_product_id",
            "purchase_receipts",
            ["received_product_id"],
        )
    if "substitution_reason" not in receipt_columns:
        op.add_column("purchase_receipts", sa.Column("substitution_reason", sa.Text(), nullable=True))

    if "work_order_revisions" not in _tables(conn):
        op.create_table(
            "work_order_revisions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("work_order_id", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(length=50), nullable=True),
            sa.Column("previous_status", sa.String(length=40), nullable=False),
            sa.Column("previous_total_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("previous_paid_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("previous_snapshot", sa.Text(), nullable=False),
            sa.Column("refund_due_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("refund_status", sa.String(length=20), nullable=False, server_default="NONE"),
            sa.Column("refund_record_id", sa.Integer(), nullable=True),
            sa.Column("reopened_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["refund_record_id"], ["refund_records.id"]),
            sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_work_order_revisions_work_order_id", "work_order_revisions", ["work_order_id"])


def downgrade():
    conn = op.get_bind()
    if "work_order_revisions" in _tables(conn):
        op.drop_table("work_order_revisions")
    receipt_columns = _columns(conn, "purchase_receipts")
    if "substitution_reason" in receipt_columns:
        op.drop_column("purchase_receipts", "substitution_reason")
    if "received_product_id" in receipt_columns:
        indexes = {index["name"] for index in inspect(conn).get_indexes("purchase_receipts")}
        if "ix_purchase_receipts_received_product_id" in indexes:
            op.drop_index("ix_purchase_receipts_received_product_id", table_name="purchase_receipts")
        op.drop_constraint("fk_purchase_receipts_received_product_id", "purchase_receipts", type_="foreignkey")
        op.drop_column("purchase_receipts", "received_product_id")
