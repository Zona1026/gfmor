"""Shared vehicle catalog and work order technician."""
from alembic import op
import sqlalchemy as sa
import json

revision = "20261122_0034"
down_revision = "20261115_0033"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('product_vehicle_models', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('work_orders', sa.Column('technician', sa.String(50), nullable=True))
    op.add_column('work_orders', sa.Column('completed_date_override', sa.Date(), nullable=True))
    with op.batch_alter_table('work_orders') as batch:
        batch.alter_column('vehicle_model', existing_type=sa.String(45), type_=sa.String(200), existing_nullable=True)
    with op.batch_alter_table('motor') as batch:
        batch.alter_column('型號', existing_type=sa.String(45), type_=sa.String(200), existing_nullable=True)
    with op.batch_alter_table('guest_motors') as batch:
        batch.alter_column('model_name', existing_type=sa.String(45), type_=sa.String(200), existing_nullable=True)
    bind = op.get_bind()
    catalog = sa.Table('product_vehicle_models', sa.MetaData(), autoload_with=bind)
    existing = set(bind.execute(sa.select(catalog.c.name)).scalars())
    names = {'通用'}
    for table_name, column_name in [('products', 'vehicle_model'), ('motor', '型號'),
                                    ('guest_motors', 'model_name'), ('work_orders', 'vehicle_model')]:
        table = sa.Table(table_name, sa.MetaData(), autoload_with=bind)
        names.update(value.strip() for value in bind.execute(sa.select(table.c[column_name])).scalars()
                     if value and value.strip())
    products = sa.Table('products', sa.MetaData(), autoload_with=bind)
    for values in bind.execute(sa.select(products.c.vehicle_models)).scalars():
        if isinstance(values, str):
            values = json.loads(values)
        names.update(value.strip() for value in (values or []) if value and value.strip())
    for name in sorted(names - existing):
        # Respect the database collation when checking duplicate names.
        if bind.execute(sa.select(catalog.c.id).where(catalog.c.name == name)).first() is None:
            bind.execute(catalog.insert().values(name=name, is_active=True))


def downgrade():
    # Keep widened columns and imported catalog entries to avoid truncating data.
    op.drop_column('work_orders', 'completed_date_override')
    op.drop_column('work_orders', 'technician')
    op.drop_column('product_vehicle_models', 'is_active')
