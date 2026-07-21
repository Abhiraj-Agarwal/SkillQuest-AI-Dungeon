"""
AccuracyHistory SQLAlchemy model — tracks per-player, per-topic performance.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, UniqueConstraint, JSON, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class AccuracyHistory(Base):
    __tablename__ = "accuracy_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False, index=True)
    topic = Column(String, nullable=False)
    attempts = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    recent_accuracy = Column(Float, default=0.0)
    last_5_results = Column(JSON, default=list)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("player_id", "topic", name="uq_player_topic"),
    )

    # Relationship
    player = relationship("Player", back_populates="accuracy_histories")
