"""Add optional brand type to the shared vehicle catalog."""
from alembic import op
import sqlalchemy as sa

revision = "20261123_0035"
down_revision = "20261122_0034"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('product_vehicle_models', sa.Column('brand_type', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('product_vehicle_models', 'brand_type')
