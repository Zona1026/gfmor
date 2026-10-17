"""Keep allocation history after a reopened work order line is removed."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0030"
down_revision = "20261017_0029"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("purchase_assignments") as batch:
        batch.alter_column("work_order_line_item_id", existing_type=sa.Integer(), nullable=True)


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text(
        "SELECT COUNT(*) FROM purchase_assignments WHERE work_order_line_item_id IS NULL"
    )).scalar():
        raise RuntimeError("Cannot restore required line IDs while detached allocation history exists.")
    with op.batch_alter_table("purchase_assignments") as batch:
        batch.alter_column("work_order_line_item_id", existing_type=sa.Integer(), nullable=False)
