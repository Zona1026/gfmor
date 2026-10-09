"""Add product barcodes and an independent extra-category catalog."""
from alembic import op
import sqlalchemy as sa

revision = '20261009_0022'
down_revision = '20261009_0021'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'barcode' not in {column['name'] for column in sa.inspect(bind).get_columns('products')}:
        op.add_column('products', sa.Column('barcode', sa.String(100), nullable=True))
    tables = sa.inspect(bind).get_table_names()
    if 'product_extra_categories' not in tables:
        op.create_table('product_extra_categories',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(100), nullable=False, unique=True),
            sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'))
    if 'product_extra_category_links' not in tables:
        op.create_table('product_extra_category_links',
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('category_id', sa.Integer(), sa.ForeignKey('product_extra_categories.id', ondelete='CASCADE'), primary_key=True))
    # Move previously selected secondary categories, preserving primary category records.
    metadata = sa.MetaData()
    products = sa.Table('products', metadata, autoload_with=bind)
    categories = sa.Table('product_categories', metadata, autoload_with=bind)
    old_links = sa.Table('product_category_links', metadata, autoload_with=bind)
    extras = sa.Table('product_extra_categories', metadata, autoload_with=bind)
    links = sa.Table('product_extra_category_links', metadata, autoload_with=bind)
    rows = bind.execute(sa.select(old_links.c.product_id, old_links.c.category_id,
                                  categories.c.name, categories.c.sort_order, categories.c.is_active)
        .join(products, products.c.id == old_links.c.product_id)
        .join(categories, categories.c.id == old_links.c.category_id)
        .where(sa.or_(products.c.category_id.is_(None), old_links.c.category_id != products.c.category_id))).mappings().all()
    for row in rows:
        extra_id = bind.execute(sa.select(extras.c.id).where(extras.c.name == row['name'])).scalar()
        if extra_id is None:
            result = bind.execute(extras.insert().values(name=row['name'], sort_order=row['sort_order'], is_active=row['is_active']))
            extra_id = result.inserted_primary_key[0]
        exists = bind.execute(sa.select(links.c.product_id).where(links.c.product_id == row['product_id'], links.c.category_id == extra_id)).first()
        if not exists:
            bind.execute(links.insert().values(product_id=row['product_id'], category_id=extra_id))
        bind.execute(old_links.delete().where(old_links.c.product_id == row['product_id'], old_links.c.category_id == row['category_id']))


def downgrade():
    op.drop_table('product_extra_category_links')
    op.drop_table('product_extra_categories')
    with op.batch_alter_table('products') as batch:
        batch.drop_column('barcode')
