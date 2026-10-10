"""Backfill member vehicle mileage from existing work orders."""

from alembic import op
import sqlalchemy as sa


revision = "20261010_0025"
down_revision = "20261010_0024"
branch_labels = None
depends_on = None


def _backfill_member_mileage(conn):
    motor = sa.table(
        "motor", sa.column("ID", sa.Integer), sa.column("Google ID", sa.String),
        sa.column("里程數", sa.Integer),
    )
    work_orders = sa.table(
        "work_orders", sa.column("motor_id", sa.Integer), sa.column("google_id", sa.String),
        sa.column("vehicle_mileage", sa.Integer), sa.column("status", sa.String),
        sa.column("deleted_at", sa.DateTime),
    )
    highest_mileage = (
        sa.select(sa.func.max(work_orders.c.vehicle_mileage))
        .where(
            work_orders.c.motor_id == motor.c["ID"],
            work_orders.c.google_id == motor.c["Google ID"],
            work_orders.c.vehicle_mileage >= 0,
            work_orders.c.status != "CANCELED",
            work_orders.c.deleted_at.is_(None),
        )
        .correlate(motor)
        .scalar_subquery()
    )
    conn.execute(
        motor.update()
        .where(
            highest_mileage.is_not(None),
            sa.or_(motor.c["里程數"].is_(None), motor.c["里程數"] < highest_mileage),
        )
        .values({"里程數": highest_mileage})
    )


def upgrade():
    _backfill_member_mileage(op.get_bind())


def downgrade():
    # Preserve observed odometer values; the prior values cannot be reconstructed.
    pass
