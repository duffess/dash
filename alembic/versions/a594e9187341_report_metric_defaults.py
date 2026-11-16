"""Store report metric defaults per user."""
from alembic import op
import sqlalchemy as sa

revision = "a594e9187341"
down_revision = "f132bd742153"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("report_default_metrics", sa.JSON(), nullable=True))

def downgrade():
    op.drop_column("users", "report_default_metrics")
