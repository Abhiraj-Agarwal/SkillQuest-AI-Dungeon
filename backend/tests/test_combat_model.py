"""
Tests for the hits-required/hits-landed combat model and the powerup rework
that unified around it (see routes/game.py's _room_correct_count, enter_room,
submit_answer, and use_powerup).

Root bug this guards against: the villain HP bar used to be an arbitrary
flat number (enemy_hp, sized off question difficulty) tracked independently
of the real win condition (correct answers >= room.enemy_count). The two
could disagree -- the bar could freeze well above or below empty relative to
when the room actually cleared. These tests assert the bar (hits_required -
hits_landed) always reaches exactly zero in the same response that reports
room_cleared, across a full room-clear sequence, including forced-correct
powerup hits.

Builds a standalone FastAPI app around just routes.game's router (not
main:app) so this never touches the real skillquest.db or triggers demo
seeding, and monkeypatches the AI-service calls so no live Gemini/services
call is made.
"""
import sys

sys.path.insert(0, ".")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from models.player import Player  # noqa: F401
from models.guild import Guild  # noqa: F401
from models.dungeon import Dungeon, Room
from models.session import GameSession  # noqa: F401
from models.question import Question  # noqa: F401
from models.submission import AnswerSubmission  # noqa: F401
from models.accuracy_history import AccuracyHistory  # noqa: F401
import routes.game as game_routes


@pytest.fixture
def client(monkeypatch):
    # StaticPool: a plain sqlite:///:memory: engine hands out a fresh, empty
    # in-memory database per connection checkout -- StaticPool pins it to a
    # single shared connection so the app's requests and this fixture's setup
    # actually see the same tables/rows.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(game_routes.router)
    app.dependency_overrides[get_db] = override_get_db

    # Deterministic stand-ins for the AI service calls -- these tests are
    # about the combat/powerup bookkeeping, not the LLM integration.
    verdict_box = {"verdict": "incorrect", "damage_multiplier": 0.0}

    async def fake_generate_question(player_id, topic, difficulty, domain):
        return {
            "question_id": f"q-{topic}-{difficulty}-{id(object())}",
            "question": f"Test question about {topic}",
            "expected_answer": "the correct answer",
            "hint": "a hint",
        }

    async def fake_judge_answer(question_id, player_answer, expected_answer):
        return {
            "score": 1.0 if verdict_box["verdict"] == "correct" else 0.0,
            "damage_multiplier": verdict_box["damage_multiplier"],
            "verdict": verdict_box["verdict"],
            "feedback": "test feedback",
        }

    async def fake_next_difficulty(player_id, topic, accuracy_map):
        return {"difficulty": "easy"}

    monkeypatch.setattr(game_routes, "call_generate_question", fake_generate_question)
    monkeypatch.setattr(game_routes, "call_judge_answer", fake_judge_answer)
    monkeypatch.setattr(game_routes, "call_next_difficulty", fake_next_difficulty)

    test_client = TestClient(app)
    test_client.verdict_box = verdict_box
    test_client._SessionLocal = TestingSessionLocal
    return test_client


def _make_dungeon_and_room(client, enemy_count=3):
    db = client._SessionLocal()
    dungeon = Dungeon(name="Test Dungeon", domain="DSA")
    db.add(dungeon)
    db.flush()
    room = Room(
        dungeon_id=dungeon.dungeon_id, topic="arrays", order_index=0,
        is_unlocked=True, enemy_count=enemy_count,
    )
    db.add(room)
    db.commit()
    dungeon_id, room_id = dungeon.dungeon_id, room.room_id
    db.close()
    return dungeon_id, room_id


def _register_and_start(client, username, dungeon_id):
    player_id = client.post("/game/player/create", json={"username": username}).json()["player_id"]
    session_id = client.post(
        "/game/session/start", json={"player_id": player_id, "dungeon_id": dungeon_id}
    ).json()["session_id"]
    return player_id, session_id


def _enter_and_submit(client, session_id, room_id, player_id, answer_text="my answer"):
    entered = client.post("/game/room/enter", json={"session_id": session_id, "room_id": room_id}).json()
    question_id = entered["question"]["question_id"]
    submitted = client.post(
        "/game/answer/submit",
        json={"player_id": player_id, "question_id": question_id, "player_answer": answer_text},
    ).json()
    return entered, submitted


def test_room_enter_reports_hits_required_matching_enemy_count(client):
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=3)
    player_id, session_id = _register_and_start(client, "alpha", dungeon_id)

    entered = client.post("/game/room/enter", json={"session_id": session_id, "room_id": room_id}).json()

    assert entered["hits_required"] == 3
    assert entered["hits_landed"] == 0


def test_hp_bar_reaches_exactly_zero_when_room_actually_clears(client):
    """The core regression test: hits_landed must reach hits_required in the
    exact same response where room_cleared flips true -- never before, never
    after."""
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=3)
    player_id, session_id = _register_and_start(client, "alpha", dungeon_id)
    client.verdict_box["verdict"] = "correct"
    client.verdict_box["damage_multiplier"] = 2.0

    for expected_hits in (1, 2, 3):
        _, result = _enter_and_submit(client, session_id, room_id, player_id)
        assert result["hits_landed"] == expected_hits
        assert result["hits_required"] == 3
        assert result["room_cleared"] == (expected_hits == 3)


def test_incorrect_answers_never_move_the_hp_bar(client):
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=3)
    player_id, session_id = _register_and_start(client, "alpha", dungeon_id)
    client.verdict_box["verdict"] = "incorrect"
    client.verdict_box["damage_multiplier"] = 0.0

    for _ in range(5):
        _, result = _enter_and_submit(client, session_id, room_id, player_id)
        assert result["hits_landed"] == 0
        assert result["room_cleared"] is False


def test_force_correct_powerup_lands_a_hit_regardless_of_judge_verdict(client):
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=3)
    player_id, session_id = _register_and_start(client, "alpha", dungeon_id)

    hero_resp = client.post(f"/game/player/{player_id}/hero", json={"hero_id": "titan_warrior"})
    assert hero_resp.status_code == 200

    powerup_resp = client.post("/game/powerup/use", json={"player_id": player_id})
    assert powerup_resp.status_code == 200
    assert powerup_resp.json()["queued"] is True

    # Judge says incorrect -- the queued force_correct should override it.
    client.verdict_box["verdict"] = "incorrect"
    client.verdict_box["damage_multiplier"] = 0.0
    _, result = _enter_and_submit(client, session_id, room_id, player_id, "definitely wrong")

    assert result["verdict"] == "correct"
    assert result["hits_landed"] == 1


def test_powerup_cooldown_enforced_after_max_uses(client):
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=5)
    player_id, _session_id = _register_and_start(client, "alpha", dungeon_id)
    client.post(f"/game/player/{player_id}/hero", json={"hero_id": "titan_warrior"})

    for _ in range(3):
        resp = client.post("/game/powerup/use", json={"player_id": player_id})
        assert resp.status_code == 200

    fourth = client.post("/game/powerup/use", json={"player_id": player_id})
    assert fourth.status_code == 429


def test_unknown_hero_id_rejected(client):
    dungeon_id, _room_id = _make_dungeon_and_room(client)
    player_id, _session_id = _register_and_start(client, "alpha", dungeon_id)

    resp = client.post(f"/game/player/{player_id}/hero", json={"hero_id": "not_a_real_hero"})
    assert resp.status_code == 422


def test_hits_landed_never_exceeds_hits_required_even_with_stray_submissions(client):
    """Guards the min(room.enemy_count, correct_count) clamp -- a player who
    somehow racks up more correct answers for a topic than the room asks for
    (e.g. replaying a room) should never show a negative or over-100% bar."""
    dungeon_id, room_id = _make_dungeon_and_room(client, enemy_count=1)
    player_id, session_id = _register_and_start(client, "alpha", dungeon_id)
    client.verdict_box["verdict"] = "correct"
    client.verdict_box["damage_multiplier"] = 2.0

    _, first = _enter_and_submit(client, session_id, room_id, player_id)
    assert first["room_cleared"] is True
    assert first["hits_landed"] == 1

    # Re-entering an already-cleared room still reports a clamped, sane value.
    entered_again = client.post(
        "/game/room/enter", json={"session_id": session_id, "room_id": room_id}
    ).json()
    assert entered_again["hits_landed"] <= entered_again["hits_required"]
