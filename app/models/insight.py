import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    insight_type = Column(String, nullable=False, default="general") 
    
    created_at = Column(DateTime, default=datetime.utcnow)

    client = relationship("Client", back_populates="insights")

    def __repr__(self):
        return f"<Insight {self.insight_type} client={self.client_id}>"
