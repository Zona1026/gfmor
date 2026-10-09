"""Add scheduled product promotions for work-order pricing."""
from alembic import op
import sqlalchemy as sa

revision = '20261010_0023'
down_revision = '20261009_0022'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('promotions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('starts_at', sa.DateTime(), nullable=False),
        sa.Column('ends_at', sa.DateTime(), nullable=False),
        sa.Column('discount_type', sa.String(20), nullable=False),
        sa.Column('discount_value', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True))
    op.create_table('promotion_product_links',
        sa.Column('promotion_id', sa.Integer(), sa.ForeignKey('promotions.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), primary_key=True))


def downgrade():
    op.drop_table('promotion_product_links')
    op.drop_table('promotions')
