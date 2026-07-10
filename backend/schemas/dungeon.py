"""
Dungeon and session Pydantic schemas.
"""
from pydantic import BaseModel
from typing import List, Optional


class RoomResponse(BaseModel):
    room_id: str
    topic: str
    enemy_count: int
    is_boss: bool
    is_unlocked: bool
    order_index: int

    class Config:
        from_attributes = True


class DungeonResponse(BaseModel):
    dungeon_id: str
    name: str
    domain: str
    rooms: List[RoomResponse] = []

    class Config:
        from_attributes = True


class SessionStartRequest(BaseModel):
    player_id: str
    dungeon_id: str


class SessionStartResponse(BaseModel):
    session_id: str
    dungeon: DungeonResponse
    current_room_id: Optional[str] = None

    class Config:
        from_attributes = True


class RoomEnterRequest(BaseModel):
    session_id: str
    room_id: str


class RoomEnterResponse(BaseModel):
    room: RoomResponse
    question: dict  # question_id, question, hint, topic, difficulty
    enemy_hp: int

    class Config:
        from_attributes = True
