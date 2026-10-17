"""Persist work order line item display order."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0027"
down_revision = "20261010_0026"
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows retain ID order when all positions are zero.
    op.add_column("work_order_line_items", sa.Column(
        "sort_order", sa.Integer(), nullable=False, server_default="0",
    ))


def downgrade():
    op.drop_column("work_order_line_items", "sort_order")
