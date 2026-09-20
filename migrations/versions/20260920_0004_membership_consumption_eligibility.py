"""Add per-line membership consumption eligibility."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260920_0004"
down_revision = "20260808_0003"
branch_labels = None
depends_on = None


def _columns(conn, table_name):
    if table_name not in set(inspect(conn).get_table_names()):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()
    if "counts_toward_membership" not in _columns(conn, "work_order_line_items"):
        with op.batch_alter_table("work_order_line_items") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "counts_toward_membership",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

    if "membership_consumption_amount" not in _columns(conn, "work_orders"):
        with op.batch_alter_table("work_orders") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "membership_consumption_amount",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )


def downgrade():
    # Keep historical membership accounting data intact on rollback.
    pass
