"""Add a separate product model number."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_0020'
down_revision = '20261009_0019'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('products')}
    if 'model_number' not in columns:
        op.add_column('products', sa.Column('model_number', sa.String(200), nullable=True))


def downgrade():
    with op.batch_alter_table('products') as batch:
        batch.drop_column('model_number')
