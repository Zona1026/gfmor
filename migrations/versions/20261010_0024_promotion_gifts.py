"""Add buy-A-get-B settings and identifiable work-order gifts."""
from alembic import op
import sqlalchemy as sa

revision = '20261010_0024'
down_revision = '20261010_0023'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('promotions', sa.Column('buy_quantity', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('promotions', sa.Column('gift_quantity', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('promotions', sa.Column('gift_product_id', sa.Integer(), nullable=True))
    op.add_column('promotions', sa.Column('allow_discount_stacking', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_foreign_key('fk_promotion_gift_product', 'promotions', 'products', ['gift_product_id'], ['id'])
    op.add_column('work_order_line_items', sa.Column('promotion_gift_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_work_order_promotion_gift', 'work_order_line_items', 'promotions', ['promotion_gift_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_work_order_promotion_gift', 'work_order_line_items', type_='foreignkey')
    op.drop_column('work_order_line_items', 'promotion_gift_id')
    op.drop_constraint('fk_promotion_gift_product', 'promotions', type_='foreignkey')
    for column in ['allow_discount_stacking', 'gift_product_id', 'gift_quantity', 'buy_quantity']:
        op.drop_column('promotions', column)
