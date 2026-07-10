"""
AI client — routes AI calls to the /ai/ endpoints (mock or real, toggled by main.py).
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = "http://localhost:8000"
DEFAULT_DOMAIN = os.getenv("DEFAULT_DOMAIN", "Data Structures & Algorithms")


async def call_generate_question(player_id: str, topic: str, difficulty: str = "medium", domain: str = None) -> dict:
    """Call the question generation endpoint (mock or real)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/ai/question/generate", json={
            "player_id": player_id, "topic": topic,
            "difficulty": difficulty, "domain": domain or DEFAULT_DOMAIN,
        }, timeout=30.0)
        return resp.json()


async def call_judge_answer(question_id: str, player_answer: str, expected_answer: str) -> dict:
    """Call the answer judge endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/ai/answer/judge", json={
            "question_id": question_id, "player_answer": player_answer,
            "expected_answer": expected_answer,
        }, timeout=30.0)
        return resp.json()


async def call_next_difficulty(player_id: str, topic: str, accuracy_history: dict = None) -> dict:
    """Call the difficulty tuner endpoint with accuracy data for RL bandit."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/ai/difficulty/next", json={
            "player_id": player_id, "topic": topic,
            "accuracy_history": accuracy_history or {},
        }, timeout=10.0)
        return resp.json()


async def call_next_topic(player_id: str, accuracy_history: dict) -> dict:
    """Call the knowledge graph routing endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/ai/graph/next-topic", json={
            "player_id": player_id, "accuracy_history": accuracy_history,
        }, timeout=10.0)
        return resp.json()
