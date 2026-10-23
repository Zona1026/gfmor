"""Archive merged guests while retaining their original profile and vehicles."""
from alembic import op
import sqlalchemy as sa

revision = "20261023_0032"
down_revision = "20261021_0031"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("guest_customers") as batch:
        batch.add_column(sa.Column("merged_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("merged_into_google_id", sa.String(255), nullable=True))
        batch.create_index("ix_guest_customers_merged_at", ["merged_at"])
        batch.create_foreign_key("fk_guest_merged_member", "users", ["merged_into_google_id"], ["Google ID"])

    # Older merges left no profile marker. Only archive profiles with evidence
    # of merged vehicles and no remaining business records or active vehicles.
    # Record the archival time; the original target member is unknown.
    op.execute(sa.text("""
        UPDATE guest_customers SET merged_at = CURRENT_TIMESTAMP
        WHERE EXISTS (
            SELECT 1 FROM guest_motors m
            WHERE m.guest_customer_id = guest_customers.id AND m.status = '已合併'
        ) AND NOT EXISTS (
            SELECT 1 FROM guest_motors m
            WHERE m.guest_customer_id = guest_customers.id AND m.status IS NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM work_orders w WHERE w.guest_customer_id = guest_customers.id
        ) AND NOT EXISTS (
            SELECT 1 FROM orders o WHERE o.guest_customer_id = guest_customers.id
        )
    """))


def downgrade():
    with op.batch_alter_table("guest_customers") as batch:
        batch.drop_constraint("fk_guest_merged_member", type_="foreignkey")
        batch.drop_index("ix_guest_customers_merged_at")
        batch.drop_column("merged_into_google_id")
        batch.drop_column("merged_at")
