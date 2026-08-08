"""Add admin email and password reset fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260808_0003"
down_revision = "20260707_0002"
branch_labels = None
depends_on = None


def _tables(conn):
    return set(inspect(conn).get_table_names())


def _columns(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def _indexes(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {index["name"] for index in inspect(conn).get_indexes(table_name)}


def _add_column_if_missing(conn, table_name, column):
    if column.name in _columns(conn, table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(column)


def _create_index_if_missing(conn, name, table_name, columns, unique=False):
    if name not in _indexes(conn, table_name):
        op.create_index(name, table_name, columns, unique=unique)


def upgrade():
    conn = op.get_bind()
    if "admins" not in _tables(conn):
        return

    _add_column_if_missing(conn, "admins", sa.Column("email", sa.String(length=255), nullable=True))
    _add_column_if_missing(conn, "admins", sa.Column("password_reset_token_hash", sa.String(length=64), nullable=True))
    _add_column_if_missing(conn, "admins", sa.Column("password_reset_expires_at", sa.DateTime(), nullable=True))
    _add_column_if_missing(conn, "admins", sa.Column("password_reset_requested_at", sa.DateTime(), nullable=True))

    _create_index_if_missing(conn, "ix_admins_email", "admins", ["email"], unique=True)
    _create_index_if_missing(
        conn,
        "ix_admins_password_reset_token_hash",
        "admins",
        ["password_reset_token_hash"],
        unique=True,
    )


def downgrade():
    # Keep admin account and recovery data intact on production rollbacks.
    pass
