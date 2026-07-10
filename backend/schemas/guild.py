"""
Guild Pydantic schemas.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict


class GuildCreate(BaseModel):
    name: str
    creator_player_id: str


class GuildResponse(BaseModel):
    guild_id: str
    name: str
    members: List[dict] = []
    raid_active: bool
    raid_boss_id: Optional[str] = None

    class Config:
        from_attributes = True


class RaidJoinRequest(BaseModel):
    guild_id: str
    player_id: str


class GuildJoinRequest(BaseModel):
    guild_id: str
    player_id: str
