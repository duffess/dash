"""Save immutable report data and the evidence used by AI analyses."""
from alembic import op
import sqlalchemy as sa

revision = "c92f482db613"
down_revision = "b47ea921c803"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("insights", sa.Column("snapshot", sa.JSON(), nullable=True))
    op.add_column("insights", sa.Column("ai_model", sa.String(), nullable=True))
    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("client_id", sa.String(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reports_client_id", "reports", ["client_id"])


def downgrade():
    op.drop_table("reports")
    with op.batch_alter_table("insights") as batch:
        batch.drop_column("ai_model")
        batch.drop_column("snapshot")
