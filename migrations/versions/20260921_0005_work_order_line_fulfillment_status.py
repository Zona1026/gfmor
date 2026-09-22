"""Add fulfillment status tracking to work order line items."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = "20260921_0005"
down_revision = "20260920_0004"
branch_labels = None
depends_on = None


def _column_exists(conn, table_name, column_name):
    if conn.dialect.name == "mysql":
        return bool(conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = :table_name "
                "AND column_name = :column_name LIMIT 1"
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar())
    if table_name not in set(inspect(conn).get_table_names()):
        return False
    return column_name in {column["name"] for column in inspect(conn).get_columns(table_name)}


def _is_duplicate_column_error(error):
    original = getattr(error, "orig", None)
    args = getattr(original, "args", ())
    return bool(args) and args[0] == 1060


def _add_column_if_missing(conn, table_name, column):
    if _column_exists(conn, table_name, column.name):
        return
    try:
        op.add_column(table_name, column)
    except (OperationalError, ProgrammingError) as error:
        if conn.dialect.name != "mysql" or not _is_duplicate_column_error(error):
            raise


def upgrade():
    conn = op.get_bind()
    _add_column_if_missing(
        conn,
        "work_order_line_items",
        sa.Column("fulfillment_status", sa.String(length=20), nullable=True),
    )
    _add_column_if_missing(
        conn,
        "work_order_line_items",
        sa.Column("fulfillment_status_updated_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    conn = op.get_bind()
    with op.batch_alter_table("work_order_line_items") as batch_op:
        if _column_exists(conn, "work_order_line_items", "fulfillment_status_updated_at"):
            batch_op.drop_column("fulfillment_status_updated_at")
        if _column_exists(conn, "work_order_line_items", "fulfillment_status"):
            batch_op.drop_column("fulfillment_status")
