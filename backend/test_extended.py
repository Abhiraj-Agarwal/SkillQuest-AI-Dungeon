"""Extended tests — guild leaderboard, dashboard, boss, raids."""
import httpx
import sys
sys.path.insert(0, ".")

BASE = "http://localhost:8000"
c = httpx.Client(timeout=10.0)

# Import all models so relationships resolve
from models.player import Player
from models.guild import Guild
from models.dungeon import Dungeon, Room
from models.session import GameSession
from models.question import Question
from models.submission import AnswerSubmission
from models.accuracy_history import AccuracyHistory

db = SessionLocal()
demo = db.query(Player).filter(Player.username == "HeroOfDSA").first()
demo_id = demo.player_id
dung = db.query(Dungeon).first()
dung_id = dung.dungeon_id
db.close()

print("=== 1. AI Dashboard ===")
r = c.get(f"{BASE}/ai/dashboard/{demo_id}")
d = r.json()
print(f"  Status: {r.status_code}")
print(f"  Topic accuracies: {d['topic_accuracies']}")
print(f"  Graph state: {d['graph_state']}")
print(f"  Score history count: {len(d['score_history'])}")
assert r.status_code == 200
assert len(d["topic_accuracies"]) > 0
assert len(d["graph_state"]) > 0

print("\n=== 2. Guild Create ===")
r = c.post(f"{BASE}/game/player/create", json={"username": "guildtester"})
p1 = r.json()["player_id"]
r = c.post(f"{BASE}/game/guild/create", json={"name": "TestGuild", "creator_player_id": p1})
print(f"  Status: {r.status_code}")
guild = r.json()
guild_id = guild["guild_id"]
print(f"  Guild: {guild['name']} (ID: {guild_id})")
assert r.status_code == 200

print("\n=== 3. Guild Leaderboard ===")
r = c.get(f"{BASE}/game/leaderboard/guild")
print(f"  Status: {r.status_code}")
print(f"  Guilds: {r.json()}")
assert r.status_code == 200

print("\n=== 4. Raid Join ===")
r = c.post(f"{BASE}/game/guild/raid/join", json={"guild_id": guild_id, "player_id": p1})
print(f"  Status: {r.status_code}")
raid = r.json()
print(f"  Assigned topic: {raid['assigned_topic']}")
print(f"  Boss HP: {raid['raid_boss_hp']}")
assert r.status_code == 200
assert raid["raid_active"] == True

print("\n=== 5. Raid Status ===")
r = c.get(f"{BASE}/game/guild/raid/status?guild_id={guild_id}")
print(f"  Status: {r.status_code}")
status = r.json()
print(f"  Active: {status['raid_active']}, HP: {status['raid_boss_hp']}, Damage: {status['raid_boss_damage']}")
assert r.status_code == 200

print("\n=== 6. Next Topic ===")
r = c.get(f"{BASE}/game/dungeon/{dung_id}/next-topic?player_id={demo_id}")
print(f"  Status: {r.status_code}")
nt = r.json()
print(f"  Next topic: {nt['next_topic']}")
print(f"  Weak topics: {nt['weak_topics']}")
assert r.status_code == 200

print("\n=== 7. Boss Room Check ===")
db = SessionLocal()
boss_room = db.query(Room).filter(Room.dungeon_id == dung_id, Room.is_boss == True).first()
print(f"  Boss room: {boss_room.topic}, enemies: {boss_room.enemy_count}, unlocked: {boss_room.is_unlocked}")
db.close()
assert boss_room.enemy_count == 5  # Boss has 5 enemies

print("\n=== 8. Hint Use ===")
# Start session, enter room, get question, try hint
r = c.post(f"{BASE}/game/session/start", json={"player_id": p1, "dungeon_id": dung_id})
sid = r.json()["session_id"]
rooms = c.get(f"{BASE}/game/dungeon/{dung_id}").json()["rooms"]
first_room = [rm for rm in rooms if rm["is_unlocked"]][0]
r = c.post(f"{BASE}/game/room/enter", json={"session_id": sid, "room_id": first_room["room_id"]})
qid = r.json()["question"]["question_id"]
r = c.post(f"{BASE}/game/hint/use", json={"player_id": p1, "question_id": qid})
print(f"  Status: {r.status_code}")
print(f"  Hint: {r.json()['hint'][:50]}...")
print(f"  Tokens remaining: {r.json()['hint_tokens_remaining']}")
assert r.status_code == 200

print("\n=== 9. Player Stats (Demo Player) ===")
r = c.get(f"{BASE}/game/player/{demo_id}")
stats = r.json()
print(f"  Level: {stats['level']}, XP: {stats['total_xp']}, Streak: {stats['streak_days']}")
print(f"  Hints: {stats['hint_tokens']}")
print(f"  Accuracy topics: {len(stats['accuracy_history'])}")
assert r.status_code == 200

print("\n=== ALL EXTENDED TESTS PASSED ===")
