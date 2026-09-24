"""Add work order consumption dates and point transaction sources."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260924_0007"
down_revision = "20260921_0006"
branch_labels = None
depends_on = None


def _tables(conn):
    return set(inspect(conn).get_table_names())


def _columns(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def _column_is_nullable(conn, table_name, column_name):
    if table_name not in _tables(conn):
        return None
    for column in inspect(conn).get_columns(table_name):
        if column["name"] == column_name:
            return column.get("nullable", True)
    return None


def _indexes(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {index["name"] for index in inspect(conn).get_indexes(table_name)}


def _has_foreign_key(conn, table_name, constrained_column):
    if table_name not in _tables(conn):
        return False
    return any(
        constrained_column in (foreign_key.get("constrained_columns") or [])
        for foreign_key in inspect(conn).get_foreign_keys(table_name)
    )


def upgrade():
    conn = op.get_bind()

    if "consumption_date" not in _columns(conn, "work_orders"):
        op.add_column(
            "work_orders",
            sa.Column("consumption_date", sa.Date(), nullable=True),
        )

    if "consumption_date" in _columns(conn, "work_orders"):
        conn.execute(sa.text("""
            UPDATE work_orders
            SET consumption_date = DATE(COALESCE(completed_at, scheduled_at, created_at, CURRENT_TIMESTAMP))
            WHERE consumption_date IS NULL
        """))

    if _column_is_nullable(conn, "work_orders", "consumption_date"):
        with op.batch_alter_table("work_orders") as batch_op:
            batch_op.alter_column(
                "consumption_date",
                existing_type=sa.Date(),
                nullable=False,
            )

    if "work_order_id" not in _columns(conn, "point_transactions"):
        op.add_column(
            "point_transactions",
            sa.Column("work_order_id", sa.Integer(), nullable=True),
        )

    if not _has_foreign_key(conn, "point_transactions", "work_order_id"):
        with op.batch_alter_table("point_transactions") as batch_op:
            batch_op.create_foreign_key(
                "fk_point_transactions_work_order_id_work_orders",
                "work_orders",
                ["work_order_id"],
                ["id"],
            )

    index_name = "ix_point_transactions_work_order_id"
    if index_name not in _indexes(conn, "point_transactions"):
        op.create_index(index_name, "point_transactions", ["work_order_id"])


def downgrade():
    conn = op.get_bind()

    index_name = "ix_point_transactions_work_order_id"
    if index_name in _indexes(conn, "point_transactions"):
        op.drop_index(index_name, table_name="point_transactions")
    if "work_order_id" in _columns(conn, "point_transactions"):
        with op.batch_alter_table("point_transactions") as batch_op:
            foreign_key_names = {
                foreign_key.get("name")
                for foreign_key in inspect(conn).get_foreign_keys("point_transactions")
                if "work_order_id" in (foreign_key.get("constrained_columns") or [])
            }
            if "fk_point_transactions_work_order_id_work_orders" in foreign_key_names:
                batch_op.drop_constraint(
                    "fk_point_transactions_work_order_id_work_orders",
                    type_="foreignkey",
                )
            batch_op.drop_column("work_order_id")
    if "consumption_date" in _columns(conn, "work_orders"):
        with op.batch_alter_table("work_orders") as batch_op:
            batch_op.drop_column("consumption_date")
