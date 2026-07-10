"""
Accuracy history Pydantic schemas.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AccuracyHistoryResponse(BaseModel):
    topic: str
    attempts: int
    correct: int
    recent_accuracy: float
    last_5_results: List[bool] = []

    class Config:
        from_attributes = True
