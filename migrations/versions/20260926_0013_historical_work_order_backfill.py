"""Add historical work order backfill audit fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260926_0013"
down_revision = "20260925_0012"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_orders")
    additions = (
        ("is_historical_backfill", sa.Boolean(), False),
        ("inventory_tracking_exempt", sa.Boolean(), False),
        ("backfilled_at", sa.DateTime(), None),
        ("backfilled_by", sa.String(length=50), None),
        ("backfill_reason", sa.Text(), None),
    )
    for name, column_type, default in additions:
        if name in columns:
            continue
        kwargs = {"nullable": default is None}
        if default is not None:
            kwargs["server_default"] = sa.false()
        op.add_column("work_orders", sa.Column(name, column_type, **kwargs))


def downgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_orders")
    for name in (
        "backfill_reason",
        "backfilled_by",
        "backfilled_at",
        "inventory_tracking_exempt",
        "is_historical_backfill",
    ):
        if name in columns:
            op.drop_column("work_orders", name)
