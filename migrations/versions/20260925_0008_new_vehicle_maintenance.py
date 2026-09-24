"""Add independent new vehicle maintenance schedules."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260925_0008"
down_revision = "20260924_0007"
branch_labels = None
depends_on = None


def _tables(conn):
    return set(inspect(conn).get_table_names())


def _columns(conn, table_name):
    if table_name not in _tables(conn):
        return set()
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def upgrade():
    conn = op.get_bind()

    for table_name in ("motor", "guest_motors"):
        columns = _columns(conn, table_name)
        if "is_new_vehicle" not in columns:
            op.add_column(
                table_name,
                sa.Column("is_new_vehicle", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
            op.create_index(f"ix_{table_name}_is_new_vehicle", table_name, ["is_new_vehicle"])
        if "purchase_date" not in columns:
            op.add_column(table_name, sa.Column("purchase_date", sa.Date(), nullable=True))

    if "new_vehicle_maintenance_records" not in _tables(conn):
        op.create_table(
            "new_vehicle_maintenance_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("motor_id", sa.Integer(), nullable=True),
            sa.Column("guest_motor_id", sa.Integer(), nullable=True),
            sa.Column("target_mileage", sa.Integer(), nullable=False),
            sa.Column("service_date", sa.Date(), nullable=True),
            sa.Column("actual_mileage", sa.Integer(), nullable=True),
            sa.Column("engine_oil", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("gear_oil", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("air_filter", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["guest_motor_id"], ["guest_motors.id"]),
            sa.ForeignKeyConstraint(["motor_id"], ["motor.ID"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_new_vehicle_maintenance_records_motor_id",
            "new_vehicle_maintenance_records",
            ["motor_id"],
        )
        op.create_index(
            "ix_new_vehicle_maintenance_records_guest_motor_id",
            "new_vehicle_maintenance_records",
            ["guest_motor_id"],
        )


def downgrade():
    conn = op.get_bind()
    if "new_vehicle_maintenance_records" in _tables(conn):
        op.drop_table("new_vehicle_maintenance_records")

    for table_name in ("guest_motors", "motor"):
        columns = _columns(conn, table_name)
        if "purchase_date" in columns:
            op.drop_column(table_name, "purchase_date")
        if "is_new_vehicle" in columns:
            index_name = f"ix_{table_name}_is_new_vehicle"
            indexes = {index["name"] for index in inspect(conn).get_indexes(table_name)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table_name)
            op.drop_column(table_name, "is_new_vehicle")
