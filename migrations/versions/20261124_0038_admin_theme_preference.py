"""Persist each administrator's theme preference."""
from alembic import op
import sqlalchemy as sa

revision = "20261124_0038"
down_revision = "20261124_0037"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('admins', sa.Column('theme_preference', sa.String(5), nullable=False, server_default='dark'))


def downgrade():
    op.drop_column('admins', 'theme_preference')
