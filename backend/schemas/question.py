"""
Question Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional


class QuestionGenerateRequest(BaseModel):
    player_id: str
    topic: str
    difficulty: str = "medium"  # easy | medium | hard
    domain: str = "Data Structures & Algorithms"


class QuestionResponse(BaseModel):
    question_id: str
    question: str
    hint: Optional[str] = None
    topic: str
    difficulty: str
    # NOTE: expected_answer is intentionally NOT sent to the client

    class Config:
        from_attributes = True


class QuestionFullResponse(BaseModel):
    """Internal use — includes expected_answer for AI judge."""
    question_id: str
    question: str
    expected_answer: str
    hint: Optional[str] = None
    topic: str
    difficulty: str

    class Config:
        from_attributes = True
