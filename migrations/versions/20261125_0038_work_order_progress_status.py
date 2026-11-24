"""Separate the editable order progress from the approval/accounting workflow."""
from alembic import op
import sqlalchemy as sa

revision = "20261125_0038"
down_revision = "20261124_0037"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_orders', sa.Column('progress_status', sa.String(50), nullable=True))
    # Only carry over unambiguous equivalents. In particular, supervisor-pending
    # orders remain blank; approval state must never imply purchasing progress.
    orders = sa.table('work_orders', sa.column('status', sa.String()),
                      sa.column('progress_status', sa.String()))
    for old, new in [('CUSTOMER_CONFIRMATION_PENDING', '已報價待客確認'),
                     ('COMPLETED', '已完單')]:
        op.execute(orders.update().where(orders.c.status == old).values(progress_status=new))


def downgrade():
    op.drop_column('work_orders', 'progress_status')
