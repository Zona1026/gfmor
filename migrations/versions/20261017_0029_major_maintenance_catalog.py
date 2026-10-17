"""Add major maintenance catalog and work order line type."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0029"
down_revision = "20261017_0028"
branch_labels = None
depends_on = None

COLUMNS = (("products", "inventory_type", "inventorytype"),
           ("work_order_line_items", "type", "workorderlineitemtype"))
VALUE = "MAJOR_MAINTENANCE"


def upgrade():
    conn = op.get_bind()
    for table, name, enum_name in COLUMNS:
        column = next(c for c in sa.inspect(conn).get_columns(table) if c["name"] == name)
        current = column["type"]
        if isinstance(current, sa.Enum):
            if conn.dialect.name in ("mysql", "mariadb"):
                values = list(dict.fromkeys([*current.enums, VALUE]))
                op.alter_column(table, name, existing_type=current, type_=sa.Enum(*values),
                                existing_nullable=column["nullable"], existing_server_default=sa.text(column["default"]) if column["default"] is not None else None)
            elif conn.dialect.name == "postgresql":
                with op.get_context().autocommit_block():
                    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{VALUE}'")
        elif conn.dialect.name != "sqlite" and getattr(current, "length", None) and current.length < len(VALUE):
            op.alter_column(table, name, existing_type=current, type_=sa.String(32),
                            existing_nullable=column["nullable"], existing_server_default=sa.text(column["default"]) if column["default"] is not None else None)


def downgrade():
    conn = op.get_bind()
    for table, name, _ in COLUMNS:
        if conn.execute(sa.text(f"SELECT COUNT(*) FROM {table} WHERE {name} = :value"), {"value": VALUE}).scalar():
            raise RuntimeError("Remove major maintenance entries before downgrading.")
    if conn.dialect.name in ("mysql", "mariadb"):
        for table, name, _ in COLUMNS:
            column = next(c for c in sa.inspect(conn).get_columns(table) if c["name"] == name)
            if isinstance(column["type"], sa.Enum):
                op.alter_column(table, name, existing_type=column["type"],
                                type_=sa.Enum(*(v for v in column["type"].enums if v != VALUE)),
                                existing_nullable=column["nullable"], existing_server_default=sa.text(column["default"]) if column["default"] is not None else None)
    # PostgreSQL labels are retained because removing one requires rebuilding its type.
