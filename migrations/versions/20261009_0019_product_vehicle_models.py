"""Persist manually added product vehicle model options."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_0019'
down_revision = '20261009_0018'
branch_labels = None
depends_on = None


def upgrade():
    if 'product_vehicle_models' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('product_vehicle_models',
                        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
                        sa.Column('name', sa.String(200), nullable=False, unique=True))


def downgrade():
    op.drop_table('product_vehicle_models')
