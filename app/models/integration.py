import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ClientIntegration(Base):
    __tablename__ = "client_integrations"
    __table_args__ = (
        UniqueConstraint("client_id", "platform", name="uq_client_platform"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)  # google_ads | meta_ads
    account_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="connected")  # connected | disconnected | error

    access_token_encrypted = Column(String, nullable=False)
    refresh_token_encrypted = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    last_sync_at = Column(DateTime, nullable=True)
    sync_error = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="integrations")
    campaigns = relationship("Campaign", back_populates="integration")

    def __repr__(self):
        return f"<ClientIntegration {self.platform} client={self.client_id}>"
