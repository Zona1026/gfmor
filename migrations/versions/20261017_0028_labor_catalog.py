"""Allow labor/service catalog entries in products."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0028"
down_revision = "20261017_0027"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    column = next(c for c in sa.inspect(conn).get_columns("products") if c["name"] == "inventory_type")
    # Older installations use VARCHAR; those already support the new value.
    if isinstance(column["type"], sa.Enum):
        if conn.dialect.name in ("mysql", "mariadb"):
            op.alter_column("products", "inventory_type", existing_type=column["type"],
                            type_=sa.Enum("SHOP", "PART", "BOTH", "LABOR"),
                            existing_nullable=False, existing_server_default="BOTH")
        elif conn.dialect.name == "postgresql":
            with op.get_context().autocommit_block():
                op.execute("ALTER TYPE inventorytype ADD VALUE IF NOT EXISTS 'LABOR'")


def downgrade():
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT COUNT(*) FROM products WHERE inventory_type = 'LABOR'")).scalar():
        raise RuntimeError("Remove labor catalog entries before downgrading; refusing to reclassify service fees as stock.")
    column = next(c for c in sa.inspect(conn).get_columns("products") if c["name"] == "inventory_type")
    if conn.dialect.name in ("mysql", "mariadb") and isinstance(column["type"], sa.Enum):
        op.alter_column("products", "inventory_type", existing_type=column["type"],
                        type_=sa.Enum("SHOP", "PART", "BOTH"),
                        existing_nullable=False, existing_server_default="BOTH")
    # PostgreSQL enum labels cannot be removed without rebuilding the type.
