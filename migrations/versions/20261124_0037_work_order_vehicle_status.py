"""Store vehicle status separately from the work order workflow status."""
from alembic import op
import sqlalchemy as sa

revision = "20261124_0037"
down_revision = "20261123_0036"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_orders', sa.Column('vehicle_status', sa.String(50), nullable=True))


def downgrade():
    op.drop_column('work_orders', 'vehicle_status')
