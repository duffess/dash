"""Only hashes of short-lived OAuth capabilities are persisted."""
from sqlalchemy import Column, DateTime, ForeignKey, String
from app.database import Base


class OAuthAttempt(Base):
    __tablename__ = "oauth_attempts"
    state_hash = Column(String(64), primary_key=True)
    browser_hash = Column(String(64), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(16), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
