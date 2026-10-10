"""Store multiple applicable vehicle models while preserving legacy models."""
from alembic import op
import sqlalchemy as sa

revision = "20261010_0026"
down_revision = "20261010_0025"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("vehicle_models", sa.JSON(), nullable=True))
    # NULL falls back to the existing single vehicle_model without rewriting data.


def downgrade():
    op.drop_column("products", "vehicle_models")
