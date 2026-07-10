"""
Question SQLAlchemy model — stores AI-generated questions.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(String, primary_key=True, default=generate_uuid)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)  # easy | medium | hard
    question_text = Column(String, nullable=False)
    expected_answer = Column(String, nullable=False)
    hint = Column(String, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
