"""Store the vehicle brand type as a work order snapshot."""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0036"
down_revision = "20261123_0035"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_orders', sa.Column('vehicle_brand_type', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('work_orders', 'vehicle_brand_type')
