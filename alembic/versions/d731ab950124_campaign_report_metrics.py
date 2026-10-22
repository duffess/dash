"""Preserve which metrics were provided (missing differs from zero)."""
from alembic import op
import sqlalchemy as sa

revision = "d731ab950124"
down_revision = "c92f482db613"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("campaigns", sa.Column("report_metrics", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_column("report_metrics")
