"""Add a separate trade wholesale price while preserving retail prices."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_0018'
down_revision = '20261009_0017'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('products')}
    if 'wholesale_price' not in columns:
        op.add_column('products', sa.Column('wholesale_price', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('products') as batch:
        batch.drop_column('wholesale_price')
