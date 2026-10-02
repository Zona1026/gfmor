"""Add responsible staff foreign key to work orders."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20261002_0016"
down_revision = "20260927_0015"
branch_labels = None
depends_on = None


FK_NAME = "fk_work_orders_responsible_staff_id_admins"
INDEX_NAME = "ix_work_orders_responsible_staff_id"
LEGACY_STAFF_ALIASES = {
    "火腿": "HAM-9999",
    "江子暢": "HAM-9999",
    "腿腿": "HAM-9999",
}


def _columns(conn, table_name):
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def _indexes(conn, table_name):
    return {index["name"] for index in inspect(conn).get_indexes(table_name)}


def _foreign_keys(conn, table_name):
    return {fk["name"] for fk in inspect(conn).get_foreign_keys(table_name)}


def _table_names(conn):
    return set(inspect(conn).get_table_names())


def _execute(conn, statement, params=None):
    conn.execute(sa.text(statement), params or {})


def _backfill_by_direct_admin_match(conn):
    _execute(
        conn,
        """
        UPDATE work_orders wo
        JOIN admins a
          ON wo.responsible_staff = a.full_name
          OR wo.responsible_staff = a.username
        SET
          wo.responsible_staff_id = a.id,
          wo.responsible_staff = COALESCE(a.full_name, a.username)
        WHERE wo.responsible_staff_id IS NULL
          AND wo.responsible_staff IS NOT NULL
        """,
    )


def _backfill_legacy_aliases(conn):
    for legacy_name, username in LEGACY_STAFF_ALIASES.items():
        _execute(
            conn,
            """
            UPDATE work_orders wo
            JOIN admins a ON a.username = :username
            SET
              wo.responsible_staff_id = a.id,
              wo.responsible_staff = COALESCE(a.full_name, a.username)
            WHERE wo.responsible_staff_id IS NULL
              AND wo.responsible_staff = :legacy_name
            """,
            {"username": username, "legacy_name": legacy_name},
        )


def upgrade():
    conn = op.get_bind()
    if "work_orders" not in _table_names(conn) or "admins" not in _table_names(conn):
        return

    if "responsible_staff_id" not in _columns(conn, "work_orders"):
        op.add_column("work_orders", sa.Column("responsible_staff_id", sa.Integer(), nullable=True))

    _backfill_legacy_aliases(conn)
    _backfill_by_direct_admin_match(conn)

    if INDEX_NAME not in _indexes(conn, "work_orders"):
        op.create_index(INDEX_NAME, "work_orders", ["responsible_staff_id"])

    if FK_NAME not in _foreign_keys(conn, "work_orders"):
        op.create_foreign_key(
            FK_NAME,
            "work_orders",
            "admins",
            ["responsible_staff_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    conn = op.get_bind()
    if "work_orders" not in _table_names(conn):
        return

    if FK_NAME in _foreign_keys(conn, "work_orders"):
        op.drop_constraint(FK_NAME, "work_orders", type_="foreignkey")

    if INDEX_NAME in _indexes(conn, "work_orders"):
        op.drop_index(INDEX_NAME, table_name="work_orders")

    if "responsible_staff_id" in _columns(conn, "work_orders"):
        op.drop_column("work_orders", "responsible_staff_id")
