"""Separate work order ordered, scheduled, and completed dates."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260925_0010"
down_revision = "20260925_0009"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def _column_is_nullable(conn, table_name, column_name):
    for column in inspect(conn).get_columns(table_name):
        if column["name"] == column_name:
            return column.get("nullable", True)
    return None


def upgrade():
    conn = op.get_bind()
    if "ordered_date" not in _columns(conn, "work_orders"):
        op.add_column("work_orders", sa.Column("ordered_date", sa.Date(), nullable=True))

    conn.execute(sa.text("""
        UPDATE work_orders
        SET ordered_date = DATE(COALESCE(consumption_date, scheduled_at, created_at, CURRENT_TIMESTAMP))
        WHERE ordered_date IS NULL
    """))

    if _column_is_nullable(conn, "work_orders", "ordered_date"):
        with op.batch_alter_table("work_orders") as batch_op:
            batch_op.alter_column(
                "ordered_date",
                existing_type=sa.Date(),
                nullable=False,
            )


def downgrade():
    conn = op.get_bind()
    if "ordered_date" in _columns(conn, "work_orders"):
        with op.batch_alter_table("work_orders") as batch_op:
            batch_op.drop_column("ordered_date")
