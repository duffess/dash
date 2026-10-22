"""Browser-bound, single-use OAuth attempts."""
from alembic import op
import sqlalchemy as sa

revision = "f132bd742153"
down_revision = "e821ac631042"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("oauth_attempts",
        sa.Column("state_hash", sa.String(64), primary_key=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_oauth_attempts_expires_at", "oauth_attempts", ["expires_at"])


def downgrade():
    op.drop_table("oauth_attempts")
