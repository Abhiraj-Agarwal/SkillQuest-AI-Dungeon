"""
End-to-end test script — tests the full game flow.
"""
import httpx
import json

BASE = "http://localhost:8000"

def test():
    client = httpx.Client(timeout=10.0)

    # 1. Health check
    r = client.get(f"{BASE}/health")
    print(f"1. Health: {r.json()}")
    assert r.status_code == 200

    # 2. Create player
    r = client.post(f"{BASE}/game/player/create", json={"username": "testplayer1"})
    print(f"2. Create player: {r.status_code} - {r.json()}")
    assert r.status_code == 200
    player = r.json()
    player_id = player["player_id"]
    print(f"   Player ID: {player_id}")

    # 3. Get player stats
    r = client.get(f"{BASE}/game/player/{player_id}")
    print(f"3. Player stats: {r.json()['username']}, Level {r.json()['level']}, XP {r.json()['total_xp']}")

    # 4. Get dungeons — find the seeded one
    # We need to find the dungeon ID. Let's query root endpoint first
    r = client.get(f"{BASE}/")
    print(f"4. Root: {r.json()}")

    # 5. We need to find the dungeon_id from the seed. Let's try to query all dungeons
    # Since there's no list endpoint, let's use the DB directly via a known dungeon
    # Actually, let's add a quick query. For now, let's read from seed output in server logs.
    # Alternative: call the seed directly
    import sys
    sys.path.insert(0, ".")
    from db.database import SessionLocal
    from models.dungeon import Dungeon

    db = SessionLocal()
    dungeon = db.query(Dungeon).first()
    if not dungeon:
        print("ERROR: No dungeon found!")
        return
    dungeon_id = dungeon.dungeon_id
    db.close()
    print(f"5. Dungeon ID: {dungeon_id}")

    # 6. Get dungeon structure
    r = client.get(f"{BASE}/game/dungeon/{dungeon_id}")
    print(f"6. Dungeon: {r.json()['name']} - {len(r.json()['rooms'])} rooms")
    rooms = r.json()["rooms"]
    unlocked_rooms = [rm for rm in rooms if rm["is_unlocked"]]
    print(f"   Unlocked rooms: {[rm['topic'] for rm in unlocked_rooms]}")

    # 7. Start session
    r = client.post(f"{BASE}/game/session/start", json={
        "player_id": player_id, "dungeon_id": dungeon_id
    })
    print(f"7. Start session: {r.status_code}")
    session = r.json()
    session_id = session["session_id"]
    print(f"   Session ID: {session_id}")

    # 8. Enter first room
    first_room_id = unlocked_rooms[0]["room_id"]
    r = client.post(f"{BASE}/game/room/enter", json={
        "session_id": session_id, "room_id": first_room_id
    })
    print(f"8. Enter room: {r.status_code}")
    room_data = r.json()
    question = room_data["question"]
    print(f"   Topic: {question['topic']}")
    print(f"   Question: {question['question']}")
    print(f"   Enemy HP: {room_data['enemy_hp']}")

    # 9. Submit a correct-ish answer
    r = client.post(f"{BASE}/game/answer/submit", json={
        "player_id": player_id,
        "question_id": question["question_id"],
        "player_answer": "O(1) constant time because arrays use direct index access",
        "response_time_ms": 5000,
    })
    print(f"9. Submit answer: {r.status_code}")
    result = r.json()
    print(f"   Verdict: {result['verdict']}")
    print(f"   Score: {result['score']}")
    print(f"   XP gained: {result['xp_gained']}")
    print(f"   Damage dealt: {result['damage_dealt']}")

    # 10. Check player stats after answer
    r = client.get(f"{BASE}/game/player/{player_id}")
    stats = r.json()
    print(f"10. Updated stats: Level {stats['level']}, XP {stats['total_xp']}, Streak {stats['streak_days']}")
    print(f"    Accuracy history: {stats['accuracy_history']}")

    # 11. Test leaderboard
    r = client.get(f"{BASE}/game/leaderboard")
    print(f"11. Leaderboard: {r.json()}")

    # 12. Test duplicate username
    r = client.post(f"{BASE}/game/player/create", json={"username": "testplayer1"})
    print(f"12. Duplicate username: {r.status_code} - {r.json()['detail']}")

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test()
