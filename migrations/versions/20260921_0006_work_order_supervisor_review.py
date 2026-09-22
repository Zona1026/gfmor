"""Add work-order-level supervisor review tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260921_0006"
down_revision = "20260921_0005"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    if table_name not in set(inspect(conn).get_table_names()):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_orders")
    with op.batch_alter_table("work_orders") as batch_op:
        if "supervisor_reviewed_at" not in columns:
            batch_op.add_column(sa.Column("supervisor_reviewed_at", sa.DateTime(), nullable=True))
        if "supervisor_reviewed_by" not in columns:
            batch_op.add_column(sa.Column("supervisor_reviewed_by", sa.String(length=50), nullable=True))


def downgrade():
    conn = op.get_bind()
    columns = _columns(conn, "work_orders")
    with op.batch_alter_table("work_orders") as batch_op:
        if "supervisor_reviewed_by" in columns:
            batch_op.drop_column("supervisor_reviewed_by")
        if "supervisor_reviewed_at" in columns:
            batch_op.drop_column("supervisor_reviewed_at")
