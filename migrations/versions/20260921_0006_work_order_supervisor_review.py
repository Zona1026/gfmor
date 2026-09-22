"""Add work-order-level supervisor review tracking."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = "20260921_0006"
down_revision = "20260921_0005"
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
        "work_orders",
        sa.Column("supervisor_reviewed_at", sa.DateTime(), nullable=True),
    )
    _add_column_if_missing(
        conn,
        "work_orders",
        sa.Column("supervisor_reviewed_by", sa.String(length=50), nullable=True),
    )


def downgrade():
    conn = op.get_bind()
    with op.batch_alter_table("work_orders") as batch_op:
        if _column_exists(conn, "work_orders", "supervisor_reviewed_by"):
            batch_op.drop_column("supervisor_reviewed_by")
        if _column_exists(conn, "work_orders", "supervisor_reviewed_at"):
            batch_op.drop_column("supervisor_reviewed_at")
