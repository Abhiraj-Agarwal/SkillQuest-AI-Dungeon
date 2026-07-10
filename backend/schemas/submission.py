"""
Answer submission Pydantic schemas.
"""
from pydantic import BaseModel
from typing import Optional


class AnswerSubmitRequest(BaseModel):
    player_id: str
    question_id: str
    player_answer: str
    response_time_ms: int = 0


class AnswerSubmitResponse(BaseModel):
    submission_id: str
    score: float
    damage_multiplier: float
    verdict: str  # correct | partial | incorrect
    feedback: Optional[str] = None
    xp_gained: int
    damage_dealt: int
    room_cleared: bool = False
    new_level: Optional[int] = None
    dungeon_completed: bool = False

    class Config:
        from_attributes = True
