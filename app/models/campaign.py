import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "platform",
            "external_id",
            name="uq_campaign_client_platform_external",
        ),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_id = Column(String, ForeignKey("client_integrations.id", ondelete="SET NULL"), nullable=True, index=True)
    platform = Column(String, nullable=False, index=True)
    external_id = Column(String, nullable=False)
    platform_account_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    objective = Column(String, nullable=True)

    budget = Column(Float, nullable=False, default=0)
    daily_budget = Column(Float, nullable=False, default=0)
    spend = Column(Float, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Float, nullable=False, default=0)
    ctr = Column(Float, nullable=False, default=0)
    cpc = Column(Float, nullable=False, default=0)
    cpm = Column(Float, nullable=False, default=0)
    report_metrics = Column(JSON, nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="campaigns")
    integration = relationship("ClientIntegration", back_populates="campaigns")

    def __repr__(self):
        return f"<Campaign {self.platform}:{self.external_id} client={self.client_id}>"

