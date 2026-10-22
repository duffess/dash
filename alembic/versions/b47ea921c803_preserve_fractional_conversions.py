"""Preserve fractional attribution values returned by ad providers."""
from alembic import op
import sqlalchemy as sa

revision = "b47ea921c803"
down_revision = "823b68e4f56d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("campaigns") as batch:
        batch.alter_column("conversions", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)


def downgrade():
    with op.batch_alter_table("campaigns") as batch:
        batch.alter_column("conversions", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
