"""
Minimal Gemini AI smoke test — uses only 3 API calls with delays.
Run this after the free-tier quota resets (usually within a few minutes).
"""
import httpx
import time
import sys
import os

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8000"
client = httpx.Client(timeout=90.0)  # Long timeout — Gemini retry has backoff

DELAY = 5  # seconds between API calls to avoid rate limit

print("=" * 60)
print("  GEMINI SMOKE TEST — 3 API calls")
print("=" * 60)

# --- Test 1: Generate a question ---
print("\n[1/3] Generating a question on 'arrays' (medium)...")
start = time.time()
r = client.post(f"{BASE}/ai/question/generate", json={
    "topic": "arrays",
    "difficulty": "medium",
    "domain": "Data Structures & Algorithms",
})
elapsed = time.time() - start
data = r.json()

is_fallback = "Explain the concept of" in data.get("question", "")
if not is_fallback:
    print(f"  OK — Gemini generated a real question ({elapsed:.1f}s)")
    print(f"  Q: {data['question']}")
    print(f"  A: {data['expected_answer'][:100]}...")
    print(f"  Hint: {data['hint']}")
else:
    print(f"  FALLBACK — Gemini failed, got generic question ({elapsed:.1f}s)")
    print(f"  Q: {data['question']}")
    print("  This means the API key quota is still exhausted.")
    print("  Wait a few minutes and try again.")

time.sleep(DELAY)

# --- Test 2: Judge a correct answer ---
print(f"\n[2/3] Judging a correct answer...")
start = time.time()
r = client.post(f"{BASE}/ai/answer/judge", json={
    "player_answer": "O(1) constant time because arrays use direct index access via pointer arithmetic",
    "expected_answer": "Array access is O(1) because arrays store elements in contiguous memory, allowing direct computation of any element's address using base address plus index times element size",
})
elapsed = time.time() - start
data = r.json()

is_word_overlap = data.get("feedback", "") in ["Good answer!", "Partially correct.", "Not quite right."]
print(f"  Verdict: {data['verdict']}, Score: {data['score']}, Dmg: {data['damage_multiplier']} ({elapsed:.1f}s)")
print(f"  Feedback: {data['feedback']}")
if not is_word_overlap:
    print(f"  OK — Gemini provided semantic feedback")
else:
    print(f"  FALLBACK — Using word-overlap judge (quota exhausted)")

time.sleep(DELAY)

# --- Test 3: Judge a wrong answer ---
print(f"\n[3/3] Judging a wrong answer...")
start = time.time()
r = client.post(f"{BASE}/ai/answer/judge", json={
    "player_answer": "Photosynthesis converts sunlight into energy",
    "expected_answer": "Binary search has O(log n) time complexity by halving the search space each step",
})
elapsed = time.time() - start
data = r.json()

print(f"  Verdict: {data['verdict']}, Score: {data['score']}, Dmg: {data['damage_multiplier']} ({elapsed:.1f}s)")
print(f"  Feedback: {data['feedback']}")

# --- Summary ---
print("\n" + "=" * 60)
if not is_fallback and not is_word_overlap:
    print("  RESULT: Gemini AI is working! All calls hit real API.")
elif is_fallback:
    print("  RESULT: API quota exhausted. Questions use fallback.")
    print("  The free tier resets daily. Try again later or add billing.")
else:
    print("  RESULT: Partial — questions work but judge uses fallback.")
print("=" * 60)
