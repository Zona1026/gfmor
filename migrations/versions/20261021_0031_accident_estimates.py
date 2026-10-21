"""Add standalone accident estimates without affecting inventory or accounting."""
from alembic import op
import sqlalchemy as sa

revision = "20261021_0031"
down_revision = "20261017_0030"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accident_estimates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_name", sa.String(100), nullable=False),
        sa.Column("customer_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("license_plate", sa.String(30), nullable=False),
        sa.Column("vehicle_model", sa.String(100), nullable=False),
        sa.Column("engine_number", sa.String(100), nullable=False),
        sa.Column("estimate_date", sa.Date(), nullable=False),
        sa.Column("opened_date", sa.Date(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("labor", sa.Integer(), nullable=False),
        sa.Column("estimator", sa.String(100), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("accident_estimates")
