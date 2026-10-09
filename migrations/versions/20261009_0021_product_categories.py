"""Allow products to belong to multiple categories."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_0021'
down_revision = '20261009_0020'
branch_labels = None
depends_on = None


def upgrade():
    if 'product_category_links' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('product_category_links',
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('category_id', sa.Integer(), sa.ForeignKey('product_categories.id', ondelete='CASCADE'), primary_key=True))
    # Existing primary categories remain available through products.category_id.


def downgrade():
    op.drop_table('product_category_links')
