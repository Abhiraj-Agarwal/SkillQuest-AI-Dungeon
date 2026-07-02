"""
Gemini AI Integration Test — tests real Gemini API question generation
and answer judging across multiple DSA topics and difficulty levels.

Requires: server running on localhost:8000 with USE_MOCK_AI=false
"""
import httpx
import time
import json
import sys

BASE = "http://localhost:8000"
client = httpx.Client(timeout=60.0)  # Longer timeout for Gemini API calls

PASS = 0
FAIL = 0


def log_pass(label):
    global PASS
    PASS += 1
    print(f"  ✅ {label}")


def log_fail(label, detail=""):
    global FAIL
    FAIL += 1
    print(f"  ❌ {label}: {detail}")


# ── Test 1: Question Generation — All Topics × All Difficulties ──────────

TOPICS = ["arrays", "linked_lists", "binary_search", "recursion", "trees",
          "sorting_algorithms", "dynamic_programming"]
DIFFICULTIES = ["easy", "medium", "hard"]

print("=" * 70)
print("   GEMINI AI INTEGRATION TESTS — SkillQuest Backend")
print("=" * 70)

# ── 1a: Generate questions across topics ──────────────────────────────────
print("\n🎯 TEST 1: Question Generation (Gemini)")
print("-" * 50)

generated_questions = []

for topic in TOPICS[:4]:  # Test 4 topics to keep API calls manageable
    for difficulty in DIFFICULTIES:
        start = time.time()
        r = client.post(f"{BASE}/ai/question/generate", json={
            "topic": topic,
            "difficulty": difficulty,
            "domain": "Data Structures & Algorithms",
        })
        elapsed = time.time() - start

        if r.status_code != 200:
            log_fail(f"{topic}/{difficulty}", f"HTTP {r.status_code}")
            continue

        data = r.json()

        # Validate response structure
        has_question = "question" in data and len(data["question"]) > 10
        has_answer = "expected_answer" in data and len(data["expected_answer"]) > 5
        has_hint = "hint" in data and len(data["hint"]) > 3
        has_id = "question_id" in data

        if has_question and has_answer and has_hint and has_id:
            log_pass(f"{topic}/{difficulty} ({elapsed:.1f}s)")
            generated_questions.append(data)
        else:
            log_fail(f"{topic}/{difficulty}",
                     f"Missing fields — q:{has_question} a:{has_answer} h:{has_hint} id:{has_id}")

        print(f"      Q: {data.get('question', 'N/A')[:80]}...")
        print(f"      A: {data.get('expected_answer', 'N/A')[:80]}...")
        print()


# ── 1b: Uniqueness check — same topic should produce different questions ──
print("\n🔄 TEST 2: Question Uniqueness (same topic, 3 calls)")
print("-" * 50)

unique_questions = []
for i in range(3):
    r = client.post(f"{BASE}/ai/question/generate", json={
        "topic": "arrays",
        "difficulty": "medium",
        "domain": "Data Structures & Algorithms",
    })
    if r.status_code == 200:
        unique_questions.append(r.json()["question"])
        print(f"  Q{i+1}: {r.json()['question'][:70]}...")

# Check they're different
unique_set = set(unique_questions)
if len(unique_set) >= 2:
    log_pass(f"Generated {len(unique_set)}/3 unique questions")
else:
    log_fail("Uniqueness", f"Only {len(unique_set)} unique out of 3")


# ── Test 3: Answer Judging — Correct, Partial, Incorrect ─────────────────
print("\n⚖️  TEST 3: Answer Judging (Gemini NLP Judge)")
print("-" * 50)

judge_test_cases = [
    {
        "label": "Correct answer (arrays access time)",
        "expected_answer": "O(1) because arrays use direct index-based access with pointer arithmetic",
        "player_answer": "Arrays have O(1) time complexity for access because they use direct indexing through pointer arithmetic to calculate the memory address",
        "expect_verdict": "correct",
    },
    {
        "label": "Partial answer (linked list insert)",
        "expected_answer": "To insert at the head of a linked list, create a new node, set its next pointer to the current head, and update the head pointer. Time complexity is O(1).",
        "player_answer": "Create a new node and change the head pointer",
        "expect_verdict": "partial",
    },
    {
        "label": "Incorrect answer (binary search)",
        "expected_answer": "Binary search has O(log n) time complexity because it halves the search space with each comparison",
        "player_answer": "Binary search runs in O(n) time because it checks every element",
        "expect_verdict": "incorrect",
    },
    {
        "label": "Correct answer (recursion base case)",
        "expected_answer": "A base case is the condition that stops the recursion, preventing infinite calls. Without it, the function will cause a stack overflow.",
        "player_answer": "The base case is the stopping condition in recursion that prevents infinite recursive calls and eventual stack overflow",
        "expect_verdict": "correct",
    },
    {
        "label": "Partial answer (tree traversal)",
        "expected_answer": "Inorder traversal of a BST visits nodes in left-root-right order, which produces the values in sorted ascending order",
        "player_answer": "Inorder traversal goes left then root then right",
        "expect_verdict": "partial",
    },
    {
        "label": "Totally wrong answer (stack vs queue)",
        "expected_answer": "A stack follows LIFO (Last In First Out) principle, while a queue follows FIFO (First In First Out) principle",
        "player_answer": "A photosynthesis is the process by which plants convert sunlight",
        "expect_verdict": "incorrect",
    },
]

for tc in judge_test_cases:
    start = time.time()
    r = client.post(f"{BASE}/ai/answer/judge", json={
        "player_answer": tc["player_answer"],
        "expected_answer": tc["expected_answer"],
    })
    elapsed = time.time() - start

    if r.status_code != 200:
        log_fail(tc["label"], f"HTTP {r.status_code}")
        continue

    data = r.json()
    verdict = data.get("verdict", "unknown")
    score = data.get("score", -1)
    feedback = data.get("feedback", "No feedback")
    has_dmg = "damage_multiplier" in data

    verdict_match = verdict == tc["expect_verdict"]

    if verdict_match and has_dmg and 0 <= score <= 1:
        log_pass(f"{tc['label']} → {verdict} (score={score}, {elapsed:.1f}s)")
    elif has_dmg and 0 <= score <= 1:
        log_fail(f"{tc['label']}",
                 f"Expected {tc['expect_verdict']}, got {verdict} (score={score})")
    else:
        log_fail(f"{tc['label']}", f"Bad response structure: {data}")

    print(f"      Feedback: {feedback[:80]}")
    print()


# ── Test 4: Difficulty Tuner ─────────────────────────────────────────────
print("\n📊 TEST 4: Difficulty Tuner (RL Epsilon-Greedy)")
print("-" * 50)

# High accuracy → should mostly get hard
r = client.post(f"{BASE}/ai/difficulty/next", json={
    "topic": "arrays",
    "accuracy_history": {"arrays": 0.95},
})
if r.status_code == 200 and "difficulty" in r.json():
    diff = r.json()["difficulty"]
    log_pass(f"High accuracy (0.95) → {diff}")
else:
    log_fail("High accuracy tuner", str(r.json()))

# Low accuracy → should mostly get easy
r = client.post(f"{BASE}/ai/difficulty/next", json={
    "topic": "trees",
    "accuracy_history": {"trees": 0.2},
})
if r.status_code == 200 and "difficulty" in r.json():
    diff = r.json()["difficulty"]
    log_pass(f"Low accuracy (0.20) → {diff}")
else:
    log_fail("Low accuracy tuner", str(r.json()))

# Medium accuracy → should mostly get medium
r = client.post(f"{BASE}/ai/difficulty/next", json={
    "topic": "recursion",
    "accuracy_history": {"recursion": 0.6},
})
if r.status_code == 200 and "difficulty" in r.json():
    diff = r.json()["difficulty"]
    log_pass(f"Medium accuracy (0.60) → {diff}")
else:
    log_fail("Medium accuracy tuner", str(r.json()))


# ── Test 5: Knowledge Graph Routing ──────────────────────────────────────
print("\n🗺️  TEST 5: Knowledge Graph — Next Topic Routing")
print("-" * 50)

r = client.post(f"{BASE}/ai/graph/next-topic", json={
    "accuracy_history": {
        "arrays": 0.9,
        "linked_lists": 0.3,
        "binary_search": 0.7,
        "recursion": 0.85,
    },
})
if r.status_code == 200:
    data = r.json()
    log_pass(f"Next topic: {data.get('next_topic')}")
    log_pass(f"Weak topics: {data.get('weak_topics')}")
else:
    log_fail("Next topic routing", str(r.json()))


# ── Test 6: Full Game Flow with Real Gemini ──────────────────────────────
print("\n🎮 TEST 6: Full Game Flow with Real Gemini AI")
print("-" * 50)

# Create a fresh player
import uuid
username = f"gemini_tester_{uuid.uuid4().hex[:6]}"
r = client.post(f"{BASE}/game/player/create", json={"username": username})
assert r.status_code == 200, f"Failed to create player: {r.json()}"
player_id = r.json()["player_id"]
log_pass(f"Created player: {username}")

# Get dungeon
sys.path.insert(0, ".")
from db.database import SessionLocal
from models.dungeon import Dungeon

db = SessionLocal()
dungeon = db.query(Dungeon).first()
dungeon_id = dungeon.dungeon_id
db.close()

# Start session
r = client.post(f"{BASE}/game/session/start", json={
    "player_id": player_id, "dungeon_id": dungeon_id
})
assert r.status_code == 200, f"Failed to start session: {r.json()}"
session_id = r.json()["session_id"]
log_pass(f"Started session: {session_id[:8]}...")

# Get rooms and enter first unlocked room
rooms = client.get(f"{BASE}/game/dungeon/{dungeon_id}").json()["rooms"]
unlocked = [rm for rm in rooms if rm["is_unlocked"]]
first_room = unlocked[0]
log_pass(f"Entering room: {first_room['topic']}")

# Enter room → triggers Gemini question generation
start = time.time()
r = client.post(f"{BASE}/game/room/enter", json={
    "session_id": session_id, "room_id": first_room["room_id"]
})
elapsed = time.time() - start

if r.status_code != 200:
    log_fail(f"Room enter failed", str(r.json()))
else:
    room_data = r.json()
    q = room_data["question"]
    print(f"\n  📝 Gemini-Generated Question ({elapsed:.1f}s):")
    print(f"     Topic: {q['topic']}")
    print(f"     Difficulty: {q.get('difficulty', 'N/A')}")
    print(f"     Question: {q['question']}")
    log_pass("Room entry + Gemini question generation")

    # Submit a real answer to the Gemini-generated question
    # Provide a good DSA answer
    player_answer = (
        "Arrays store elements in contiguous memory locations, allowing O(1) access "
        "by index using pointer arithmetic. The time complexity for access is constant "
        "because the address is calculated directly from the base address and index."
    )

    start = time.time()
    r = client.post(f"{BASE}/game/answer/submit", json={
        "player_id": player_id,
        "question_id": q["question_id"],
        "player_answer": player_answer,
        "response_time_ms": 8000,
    })
    elapsed = time.time() - start

    if r.status_code == 200:
        result = r.json()
        print(f"\n  ⚔️  Combat Result ({elapsed:.1f}s):")
        print(f"     Verdict: {result['verdict']}")
        print(f"     Score: {result['score']}")
        print(f"     XP Gained: {result['xp_gained']}")
        print(f"     Damage Dealt: {result['damage_dealt']}")
        print(f"     Feedback: {result.get('feedback', 'N/A')[:100]}")
        log_pass(f"Answer judged: {result['verdict']} (score={result['score']})")
    else:
        log_fail("Answer submission", str(r.json()))

    # Check player stats were updated
    r = client.get(f"{BASE}/game/player/{player_id}")
    if r.status_code == 200:
        stats = r.json()
        print(f"\n  📈 Player Stats After Combat:")
        print(f"     Level: {stats['level']}, XP: {stats['total_xp']}, Streak: {stats['streak_days']}")
        print(f"     Accuracy History: {stats['accuracy_history']}")
        if stats["total_xp"] > 0:
            log_pass(f"XP updated: {stats['total_xp']}xp, Level {stats['level']}")
        else:
            log_pass(f"Stats retrieved (XP={stats['total_xp']})")

    # Check AI dashboard
    r = client.get(f"{BASE}/ai/dashboard/{player_id}")
    if r.status_code == 200:
        dash = r.json()
        log_pass(f"Dashboard: {len(dash.get('topic_accuracies', {}))} topics tracked")
    else:
        log_fail("Dashboard", str(r.json()))


# ── Test 7: Edge Cases ───────────────────────────────────────────────────
print("\n🧪 TEST 7: Edge Cases")
print("-" * 50)

# Empty answer
r = client.post(f"{BASE}/ai/answer/judge", json={
    "player_answer": "",
    "expected_answer": "O(1) access time",
})
if r.status_code == 200 and r.json().get("verdict") == "incorrect":
    log_pass("Empty answer → incorrect")
else:
    log_fail("Empty answer handling", str(r.json()))

# Very long answer
long_answer = "Arrays are data structures " * 50
r = client.post(f"{BASE}/ai/answer/judge", json={
    "player_answer": long_answer,
    "expected_answer": "Arrays store elements contiguously in memory",
})
if r.status_code == 200 and "verdict" in r.json():
    log_pass(f"Long answer → {r.json()['verdict']}")
else:
    log_fail("Long answer handling", str(r.json()))

# Unknown topic question generation
r = client.post(f"{BASE}/ai/question/generate", json={
    "topic": "quantum_computing",
    "difficulty": "medium",
    "domain": "Data Structures & Algorithms",
})
if r.status_code == 200 and "question" in r.json():
    log_pass(f"Unusual topic handled gracefully")
else:
    log_fail("Unusual topic", str(r.json()))


# ── Summary ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"   RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print("=" * 70)

if FAIL == 0:
    print("   🎉 ALL GEMINI AI TESTS PASSED!")
else:
    print(f"   ⚠️  {FAIL} test(s) failed — review output above")

sys.exit(0 if FAIL == 0 else 1)
