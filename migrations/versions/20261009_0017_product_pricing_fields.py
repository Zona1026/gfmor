"""Add product specifications, quote standards and supplier purchase prices."""

from alembic import op
import sqlalchemy as sa

revision = '20261009_0017'
down_revision = '20261002_0016'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name']: column for column in sa.inspect(op.get_bind()).get_columns('products')}
    for column in (
        sa.Column('vehicle_model', sa.String(200), nullable=True),
        sa.Column('specification', sa.String(500), nullable=True),
        sa.Column('color', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(200), nullable=True),
        sa.Column('suggested_price', sa.Integer(), nullable=True),
        sa.Column('installation_labor', sa.Integer(), nullable=True),
        sa.Column('supplier_prices', sa.JSON(), nullable=True),
    ):
        if column.name not in columns:
            op.add_column('products', column)
    # Preserve old products; their quote standards remain unset until entered.
    products = sa.table('products', sa.column('supplier_prices', sa.JSON()))
    op.execute(products.update().where(products.c.supplier_prices.is_(None)).values(supplier_prices=[]))
    # Allow older application versions to insert products without this field.
    if not columns.get('supplier_prices', {}).get('nullable', True):
        with op.batch_alter_table('products') as batch:
            batch.alter_column('supplier_prices', existing_type=sa.JSON(), nullable=True)


def downgrade():
    with op.batch_alter_table('products') as batch:
        for field in ('supplier_prices', 'installation_labor', 'suggested_price', 'manufacturer', 'color', 'specification', 'vehicle_model'):
            batch.drop_column(field)
