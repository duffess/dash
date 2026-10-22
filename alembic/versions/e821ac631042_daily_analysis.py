"""Reserve one AI generation per client and Brasilia calendar day."""
from alembic import op
import sqlalchemy as sa

revision = "e821ac631042"
down_revision = "d731ab950124"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("daily_analyses",
        sa.Column("client_id", sa.String(), sa.ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("insight_id", sa.String(), sa.ForeignKey("insights.id", ondelete="CASCADE"), nullable=True))


def downgrade():
    op.drop_table("daily_analyses")
