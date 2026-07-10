"""
Game routes — all /game/ endpoints owned by P2.
"""
import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.player import Player
from models.dungeon import Dungeon, Room
from models.session import GameSession
from models.question import Question
from models.submission import AnswerSubmission
from models.accuracy_history import AccuracyHistory
from models.guild import Guild
from schemas.player import PlayerCreate, PlayerResponse
from schemas.dungeon import (
    DungeonResponse, SessionStartRequest, SessionStartResponse,
    RoomEnterRequest, RoomEnterResponse,
)
from schemas.submission import AnswerSubmitRequest, AnswerSubmitResponse
from schemas.guild import GuildCreate, GuildResponse, GuildJoinRequest, RaidJoinRequest
from services.game_logic import (
    calculate_xp, calculate_level, calculate_damage,
    check_room_clear, update_streak, update_accuracy_history,
    calculate_streak_bonus, BOSS_XP_BONUS, DUNGEON_COMPLETE_BONUS,
    check_dungeon_complete,
)
from services.ai_client import call_generate_question, call_judge_answer, call_next_difficulty, call_next_topic

router = APIRouter(prefix="/game", tags=["Game"])


# ─── Player Management ───

@router.post("/player/create", response_model=PlayerResponse)
async def create_player(body: PlayerCreate, db: Session = Depends(get_db)):
    existing = db.query(Player).filter(Player.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    player = Player(username=body.username)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.get("/player/{player_id}")
async def get_player(player_id: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    histories = db.query(AccuracyHistory).filter(AccuracyHistory.player_id == player_id).all()
    return {
        "player_id": player.player_id, "username": player.username,
        "level": player.level, "total_xp": player.total_xp,
        "streak_days": player.streak_days,
        "last_active": player.last_active.isoformat() if player.last_active else None,
        "guild_id": player.guild_id, "hint_tokens": player.hint_tokens,
        "accuracy_history": [
            {"topic": h.topic, "attempts": h.attempts, "correct": h.correct, "recent_accuracy": h.recent_accuracy}
            for h in histories
        ],
    }


@router.get("/player/by-username/{username}")
async def get_player_by_username(username: str, db: Session = Depends(get_db)):
    """Look up a player by username — needed for login/lookup flows."""
    player = db.query(Player).filter(Player.username == username).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    histories = db.query(AccuracyHistory).filter(AccuracyHistory.player_id == player.player_id).all()
    return {
        "player_id": player.player_id, "username": player.username,
        "level": player.level, "total_xp": player.total_xp,
        "streak_days": player.streak_days,
        "last_active": player.last_active.isoformat() if player.last_active else None,
        "guild_id": player.guild_id, "hint_tokens": player.hint_tokens,
        "accuracy_history": [
            {"topic": h.topic, "attempts": h.attempts, "correct": h.correct, "recent_accuracy": h.recent_accuracy}
            for h in histories
        ],
    }


# ─── Dungeon & Session ───

@router.get("/dungeons")
async def list_dungeons(db: Session = Depends(get_db)):
    """List all available dungeons — needed for dungeon selection screen."""
    dungeons = db.query(Dungeon).all()
    return [
        {
            "dungeon_id": d.dungeon_id, "name": d.name, "domain": d.domain,
            "room_count": len(d.rooms),
        }
        for d in dungeons
    ]


@router.get("/dungeon/{dungeon_id}", response_model=DungeonResponse)
async def get_dungeon(dungeon_id: str, db: Session = Depends(get_db)):
    dungeon = db.query(Dungeon).filter(Dungeon.dungeon_id == dungeon_id).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    return dungeon


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(body: SessionStartRequest, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == body.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    dungeon = db.query(Dungeon).filter(Dungeon.dungeon_id == body.dungeon_id).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    existing_topics = {
        history.topic
        for history in db.query(AccuracyHistory).filter(
            AccuracyHistory.player_id == body.player_id
        ).all()
    }
    for room in dungeon.rooms:
        if room.topic not in existing_topics:
            db.add(AccuracyHistory(player_id=body.player_id, topic=room.topic))

    new_streak, new_last = update_streak(player.last_active, player.streak_days)
    player.streak_days = new_streak
    player.last_active = new_last

    first_room = db.query(Room).filter(
        Room.dungeon_id == dungeon.dungeon_id, Room.is_unlocked == True
    ).order_by(Room.order_index).first()

    session = GameSession(
        player_id=body.player_id, dungeon_id=body.dungeon_id,
        current_room_id=first_room.room_id if first_room else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionStartResponse(session_id=session.session_id, dungeon=dungeon, current_room_id=session.current_room_id)


# ─── Room Entry ───

@router.post("/room/enter", response_model=RoomEnterResponse)
async def enter_room(body: RoomEnterRequest, db: Session = Depends(get_db)):
    session = db.query(GameSession).filter(GameSession.session_id == body.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    room = db.query(Room).filter(Room.room_id == body.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.is_unlocked:
        raise HTTPException(status_code=400, detail="Room is locked")

    session.current_room_id = room.room_id

    # Get dungeon info for context
    dungeon = db.query(Dungeon).filter(Dungeon.dungeon_id == session.dungeon_id).first()
    domain = dungeon.domain if dungeon else None

    # Boss rooms: force hard difficulty + cycle topics from across the dungeon
    if room.is_boss:
        difficulty = "hard"
        # Pick a random topic from all rooms in this dungeon (multi-topic boss fight)
        all_rooms = db.query(Room).filter(
            Room.dungeon_id == session.dungeon_id, Room.is_boss == False
        ).all()
        question_topic = random.choice(all_rooms).topic if all_rooms else room.topic
    else:
        # Normal rooms: use RL difficulty tuner
        histories = db.query(AccuracyHistory).filter(
            AccuracyHistory.player_id == session.player_id
        ).all()
        accuracy_map = {h.topic: h.recent_accuracy for h in histories}
        difficulty_data = await call_next_difficulty(session.player_id, room.topic, accuracy_map)
        difficulty = difficulty_data.get("difficulty", "medium")
        question_topic = room.topic

    question_data = await call_generate_question(session.player_id, question_topic, difficulty, domain)
    question = Question(
        question_id=question_data["question_id"], topic=room.topic, difficulty=difficulty,
        question_text=question_data["question"], expected_answer=question_data["expected_answer"],
        hint=question_data.get("hint", ""),
    )
    db.add(question)
    db.commit()

    enemy_hp = {"easy": 50, "medium": 100, "hard": 150}.get(difficulty, 100)
    return RoomEnterResponse(
        room=room,
        question={"question_id": question.question_id, "question": question.question_text,
                  "hint": question.hint, "topic": question.topic, "difficulty": question.difficulty},
        enemy_hp=enemy_hp,
    )


# ─── Answer Submission (CRITICAL PATH) ───

@router.post("/answer/submit", response_model=AnswerSubmitResponse)
async def submit_answer(body: AnswerSubmitRequest, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == body.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    question = db.query(Question).filter(Question.question_id == body.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    judge = await call_judge_answer(body.question_id, body.player_answer, question.expected_answer)
    score, damage_multiplier, verdict = judge["score"], judge["damage_multiplier"], judge["verdict"]
    feedback = judge.get("feedback", "")

    xp_gained = calculate_xp(question.difficulty, verdict, body.response_time_ms)

    # Streak bonus XP
    streak_bonus = calculate_streak_bonus(player.streak_days) if verdict in ("correct", "partial") else 0
    xp_gained += streak_bonus

    damage_dealt = calculate_damage(damage_multiplier, player.level)
    player.total_xp += xp_gained
    old_level = player.level
    player.level = calculate_level(player.total_xp)
    new_level = player.level if player.level > old_level else None

    old_streak = player.streak_days
    new_streak, new_last = update_streak(player.last_active, player.streak_days)
    player.streak_days = new_streak
    player.last_active = new_last

    # Hint replenishment: +1 token every time streak crosses a multiple of 5
    if new_streak > 0 and new_streak % 5 == 0 and old_streak < new_streak:
        player.hint_tokens += 1

    # *** CRITICAL: Update accuracy_history ***
    acc = db.query(AccuracyHistory).filter(
        AccuracyHistory.player_id == body.player_id, AccuracyHistory.topic == question.topic
    ).first()
    if not acc:
        acc = AccuracyHistory(player_id=body.player_id, topic=question.topic)
        db.add(acc)
        db.flush()

    new_l5, new_att, new_cor, new_acc = update_accuracy_history(
        acc.last_5_results or [], verdict, acc.attempts, acc.correct
    )
    acc.last_5_results = new_l5
    acc.attempts = new_att
    acc.correct = new_cor
    acc.recent_accuracy = new_acc

    submission = AnswerSubmission(
        player_id=body.player_id, question_id=body.question_id,
        player_answer=body.player_answer, score=score, damage_multiplier=damage_multiplier,
        verdict=verdict, response_time_ms=body.response_time_ms,
    )
    db.add(submission)

    # Check room clear
    room_cleared = False
    dungeon_completed = False
    active_session = db.query(GameSession).filter(
        GameSession.player_id == body.player_id, GameSession.status == "active"
    ).first()
    if active_session and active_session.current_room_id:
        room = db.query(Room).filter(Room.room_id == active_session.current_room_id).first()
        if room:
            correct_count = db.query(AnswerSubmission).join(Question).filter(
                AnswerSubmission.player_id == body.player_id, Question.topic == room.topic,
                AnswerSubmission.verdict == "correct",
            ).count()
            if verdict == "correct":
                correct_count += 1
            room_cleared = check_room_clear(correct_count, room.enemy_count)
            if room_cleared:
                _unlock_dependent_rooms(db, room, active_session.dungeon_id)

                # Check dungeon completion — all rooms cleared?
                all_rooms = db.query(Room).filter(Room.dungeon_id == active_session.dungeon_id).all()
                room_statuses = []
                for r in all_rooms:
                    rc = db.query(AnswerSubmission).join(Question).filter(
                        AnswerSubmission.player_id == body.player_id,
                        Question.topic == r.topic,
                        AnswerSubmission.verdict == "correct",
                    ).count()
                    # Include the current correct answer if it's for this room's topic
                    if verdict == "correct" and r.topic == room.topic:
                        pass  # already counted above
                    room_statuses.append((rc, r.enemy_count))

                dungeon_completed = check_dungeon_complete(room_statuses)
                if dungeon_completed:
                    active_session.status = "completed"
                    # Boss defeat bonus if boss room
                    if room.is_boss:
                        xp_gained += BOSS_XP_BONUS
                        player.total_xp += BOSS_XP_BONUS
                    # Dungeon completion bonus
                    xp_gained += DUNGEON_COMPLETE_BONUS
                    player.total_xp += DUNGEON_COMPLETE_BONUS
                    player.level = calculate_level(player.total_xp)
                    # Hint replenishment: +1 on dungeon complete
                    player.hint_tokens += 1

    db.commit()
    return AnswerSubmitResponse(
        submission_id=submission.submission_id, score=score, damage_multiplier=damage_multiplier,
        verdict=verdict, feedback=feedback, xp_gained=xp_gained, damage_dealt=damage_dealt,
        room_cleared=room_cleared, new_level=new_level,
        dungeon_completed=dungeon_completed,
    )


def _unlock_dependent_rooms(db: Session, cleared_room: Room, dungeon_id: str):
    from services.knowledge_graph import TOPIC_GRAPH
    for topic, prereqs in TOPIC_GRAPH.items():
        if cleared_room.topic in prereqs:
            all_met = all(
                (r := db.query(Room).filter(Room.dungeon_id == dungeon_id, Room.topic == p).first()) and r.is_unlocked
                for p in prereqs
            )
            if all_met:
                t = db.query(Room).filter(Room.dungeon_id == dungeon_id, Room.topic == topic).first()
                if t and not t.is_unlocked:
                    t.is_unlocked = True


# ─── Next Topic Routing (Knowledge Graph AI) ───

@router.get("/dungeon/{dungeon_id}/next-topic")
async def get_next_topic_for_player(dungeon_id: str, player_id: str, db: Session = Depends(get_db)):
    """Use the knowledge graph AI to recommend the next room/topic for a player."""
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    dungeon = db.query(Dungeon).filter(Dungeon.dungeon_id == dungeon_id).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    # Build accuracy map
    histories = db.query(AccuracyHistory).filter(
        AccuracyHistory.player_id == player_id
    ).all()
    accuracy_map = {h.topic: h.recent_accuracy for h in histories}

    # Call AI graph routing
    result = await call_next_topic(player_id, accuracy_map)
    next_topic = result.get("next_topic", "arrays")
    weak_topics = result.get("weak_topics", [])

    # Find the corresponding room in this dungeon
    recommended_room = db.query(Room).filter(
        Room.dungeon_id == dungeon_id, Room.topic == next_topic
    ).first()

    return {
        "next_topic": next_topic,
        "weak_topics": weak_topics,
        "recommended_room": {
            "room_id": recommended_room.room_id,
            "topic": recommended_room.topic,
            "is_unlocked": recommended_room.is_unlocked,
            "is_boss": recommended_room.is_boss,
        } if recommended_room else None,
    }


# ─── Hint System ───

@router.post("/hint/use")
async def use_hint(body: dict, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == body.get("player_id")).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.hint_tokens <= 0:
        raise HTTPException(status_code=400, detail="No hint tokens remaining")
    question = db.query(Question).filter(Question.question_id == body.get("question_id")).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    player.hint_tokens -= 1
    db.commit()
    return {"hint": question.hint, "hint_tokens_remaining": player.hint_tokens}


# ─── Leaderboard ───

@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.total_xp.desc()).offset(offset).limit(limit).all()
    return [{"rank": offset + i + 1, "player_id": p.player_id,
             "username": p.username, "level": p.level,
             "total_xp": p.total_xp, "streak_days": p.streak_days} for i, p in enumerate(players)]


@router.get("/leaderboard/guild")
async def get_guild_leaderboard(limit: int = 10, db: Session = Depends(get_db)):
    """Guild leaderboard — ranked by combined member XP."""
    from sqlalchemy import func
    results = (
        db.query(
            Guild.guild_id, Guild.name,
            func.count(Player.player_id).label("member_count"),
            func.sum(Player.total_xp).label("combined_xp"),
        )
        .join(Player, Player.guild_id == Guild.guild_id)
        .group_by(Guild.guild_id, Guild.name)
        .order_by(func.sum(Player.total_xp).desc())
        .limit(limit)
        .all()
    )
    return [
        {"rank": i + 1, "guild_id": r.guild_id, "name": r.name,
         "member_count": r.member_count, "combined_xp": r.combined_xp or 0}
        for i, r in enumerate(results)
    ]


# ─── Guild ───

@router.post("/guild/create", response_model=GuildResponse)
async def create_guild(body: GuildCreate, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == body.creator_player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if db.query(Guild).filter(Guild.name == body.name).first():
        raise HTTPException(status_code=400, detail="Guild name taken")
    guild = Guild(name=body.name)
    db.add(guild)
    db.flush()
    player.guild_id = guild.guild_id
    db.commit()
    db.refresh(guild)
    return GuildResponse(guild_id=guild.guild_id, name=guild.name,
                         members=[{"player_id": player.player_id, "username": player.username}],
                         raid_active=False)

@router.post("/guild/join")
async def join_guild(body: GuildJoinRequest, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_id == body.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    guild = db.query(Guild).filter(Guild.guild_id == body.guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    player.guild_id = guild.guild_id
    db.commit()
    return {"message": "Joined guild", "guild_id": guild.guild_id}

@router.post("/guild/raid/join")
async def join_raid(body: RaidJoinRequest, db: Session = Depends(get_db)):
    guild = db.query(Guild).filter(Guild.guild_id == body.guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    player = db.query(Player).filter(Player.player_id == body.player_id).first()
    if not player or player.guild_id != guild.guild_id:
        raise HTTPException(status_code=400, detail="Player not in this guild")

    if not guild.raid_active:
        guild.raid_active = True
        guild.raid_boss_id = str(uuid.uuid4())
        members = db.query(Player).filter(Player.guild_id == guild.guild_id).all()
        guild.raid_boss_hp = len(members) * 3  # 3 questions per member
        guild.raid_boss_damage = 0

    # Assign topic to player based on weakest area
    histories = db.query(AccuracyHistory).filter(
        AccuracyHistory.player_id == body.player_id
    ).all()
    if histories:
        weakest = min(histories, key=lambda h: h.recent_accuracy)
        assigned_topic = weakest.topic
    else:
        assigned_topic = "arrays"  # default for new players

    assignments = dict(guild.raid_topic_assignments or {})
    assignments[body.player_id] = assigned_topic
    guild.raid_topic_assignments = assignments

    db.commit()
    return {
        "message": "Joined raid", "raid_boss_id": guild.raid_boss_id,
        "raid_active": True, "assigned_topic": assigned_topic,
        "raid_boss_hp": guild.raid_boss_hp,
        "raid_boss_damage": guild.raid_boss_damage,
    }


@router.post("/guild/raid/submit")
async def submit_raid_answer(body: dict, db: Session = Depends(get_db)):
    """Submit an answer during a guild raid. Tracks combined damage to raid boss."""
    guild_id = body.get("guild_id")
    player_id = body.get("player_id")
    question_id = body.get("question_id")
    player_answer = body.get("player_answer", "")
    response_time_ms = body.get("response_time_ms", 0)

    guild = db.query(Guild).filter(Guild.guild_id == guild_id).first()
    if not guild or not guild.raid_active:
        raise HTTPException(status_code=400, detail="No active raid")
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player or player.guild_id != guild.guild_id:
        raise HTTPException(status_code=400, detail="Player not in this guild")
    question = db.query(Question).filter(Question.question_id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Judge the answer
    judge = await call_judge_answer(question_id, player_answer, question.expected_answer)
    verdict = judge["verdict"]
    score = judge["score"]

    # Award XP to the player
    xp_gained = calculate_xp(question.difficulty, verdict, response_time_ms)
    player.total_xp += xp_gained
    player.level = calculate_level(player.total_xp)

    # Deal damage to raid boss
    damage = 1 if verdict == "correct" else 0
    guild.raid_boss_damage = (guild.raid_boss_damage or 0) + damage

    raid_complete = guild.raid_boss_damage >= guild.raid_boss_hp
    if raid_complete:
        guild.raid_active = False
        # Bonus XP for all guild members on raid success
        raid_members = db.query(Player).filter(Player.guild_id == guild.guild_id).all()
        for m in raid_members:
            m.total_xp += 50  # raid completion bonus
            m.level = calculate_level(m.total_xp)

    db.commit()
    return {
        "verdict": verdict, "score": score, "xp_gained": xp_gained,
        "raid_boss_hp": guild.raid_boss_hp,
        "raid_boss_damage": guild.raid_boss_damage,
        "raid_complete": raid_complete,
        "feedback": judge.get("feedback", ""),
    }


@router.get("/guild/raid/status")
async def get_raid_status(guild_id: str, db: Session = Depends(get_db)):
    """Get current raid state for a guild."""
    guild = db.query(Guild).filter(Guild.guild_id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    members = db.query(Player).filter(Player.guild_id == guild_id).all()
    return {
        "guild_id": guild.guild_id,
        "raid_active": guild.raid_active,
        "raid_boss_id": guild.raid_boss_id,
        "raid_boss_hp": guild.raid_boss_hp or 0,
        "raid_boss_damage": guild.raid_boss_damage or 0,
        "topic_assignments": guild.raid_topic_assignments or {},
        "members": [{"player_id": m.player_id, "username": m.username} for m in members],
    }


@router.get("/guild/{guild_id}", response_model=GuildResponse)
async def get_guild(guild_id: str, db: Session = Depends(get_db)):
    guild = db.query(Guild).filter(Guild.guild_id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    members = db.query(Player).filter(Player.guild_id == guild_id).all()
    return GuildResponse(guild_id=guild.guild_id, name=guild.name,
                         members=[{"player_id": m.player_id, "username": m.username} for m in members],
                         raid_active=guild.raid_active, raid_boss_id=guild.raid_boss_id)
