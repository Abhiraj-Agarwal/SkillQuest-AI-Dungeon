"""
Player Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PlayerCreate(BaseModel):
    username: str


class PlayerResponse(BaseModel):
    player_id: str
    username: str
    level: int
    total_xp: int
    streak_days: int
    last_active: Optional[datetime] = None
    guild_id: Optional[str] = None
    hint_tokens: int

    class Config:
        from_attributes = True


class PlayerStatsResponse(BaseModel):
    player_id: str
    username: str
    level: int
    total_xp: int
    streak_days: int
    hint_tokens: int

    class Config:
        from_attributes = True
