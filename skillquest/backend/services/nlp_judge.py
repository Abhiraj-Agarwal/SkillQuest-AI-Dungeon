"""
NLP Answer Judge (P3-owned, README section 4.2).

NO P2 DEPENDENCY for the core scoring path. Both player_answer and
expected_answer arrive directly in the request body -- this module never
needs to look anything up itself.
"""

import numpy as np
from google import genai
from google.genai import types
from sentence_transformers import SentenceTransformer

import config

# Loaded once at import time -- this is a ~80MB model, reloading it per
# request would tank latency on every single answer submission.
_model = SentenceTransformer("all-MiniLM-L6-v2")
_client = genai.Client(api_key=config.GEMINI_API_KEY)

FALLBACK_PROMPT_TEMPLATE = """Given question: {question}
Expected answer: {expected_answer}
Student answered: {player_answer}
Is the student's answer essentially correct? Reply only: yes / partial / no"""

# DECISION (locked with user): the LLM fallback is a *clean override*. When
# it fires, score and damage_multiplier are snapped to the verdict's
# canonical values below, rather than blended with the original cosine score.
_CLEAN_OVERRIDE = {
    "correct": (1.0, 2.0),
    "partial": (0.5, 1.0),
    "incorrect": (0.0, 0.0),
}
_MULTIPLIER_BY_VERDICT = {"correct": 2.0, "partial": 1.0, "incorrect": 0.0}

_FEEDBACK_BY_VERDICT = {
    "correct": "Correct! Your answer captures the key idea this question was testing.",
    "partial": "Partially correct — you're on the right track, but your answer is missing some important detail.",
    "incorrect": "Incorrect — your answer doesn't match what this question was testing for.",
}


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    similarity = float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))
    return max(0.0, min(1.0, similarity))  # clamp float drift outside [0, 1]


def _verdict_from_score(score: float) -> str:
    if score >= config.JUDGE_CORRECT_THRESHOLD:
        return "correct"
    elif score >= config.JUDGE_PARTIAL_THRESHOLD:
        return "partial"
    return "incorrect"


async def _llm_fallback_verdict(question: str, expected_answer: str, player_answer: str) -> str:
    """Secondary Gemini call for scores landing in the borderline range."""
    prompt = FALLBACK_PROMPT_TEMPLATE.format(
        question=question, expected_answer=expected_answer, player_answer=player_answer
    )
    response = await _client.aio.models.generate_content(
        model=config.LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=10,
            temperature=0.0,
        ),
    )
    reply = (response.text or "").strip().lower()
    if "yes" in reply:
        return "correct"
    if "partial" in reply:
        return "partial"
    if "no" in reply:
        return "incorrect"
    # Fallback call returned something unparseable -- fall back to the
    # threshold-based verdict rather than crashing the answer-submit flow.
    return _verdict_from_score((config.JUDGE_FALLBACK_RANGE_LOW + config.JUDGE_FALLBACK_RANGE_HIGH) / 2)


# INTEGRATION NOTE: In production, expected_answer comes from the Question
# record that Person 2 stored when POST /game/room/enter was called. Person 2
# retrieves it by question_id and passes it here. For solo testing, we pass
# expected_answer directly in the request body (see tests/test_nlp_judge.py).
async def judge_answer(player_answer: str, expected_answer: str, question: str) -> dict:
    """
    Score a player's free-text answer against the expected answer.

    Inputs:
        player_answer: str -- raw text the player typed in combat.
        expected_answer: str -- from the Question record (see integration
            note above).
        question: str -- only used if the LLM fallback fires, to give the
            adjudicator full context.

    Output:
        dict matching the POST /ai/answer/judge response contract:
        { score, damage_multiplier, verdict, feedback }

    P2 dependency: NONE for this function's inputs (both strings are
    supplied by the caller). Fully testable solo.
    """
    if not player_answer or not player_answer.strip():
        return {
            "score": 0.0,
            "damage_multiplier": 0.0,
            "verdict": "incorrect",
            "feedback": "No answer was submitted, so no credit can be given for this question.",
        }

    embeddings = _model.encode([player_answer, expected_answer])
    score = _cosine_similarity(embeddings[0], embeddings[1])

    if config.JUDGE_FALLBACK_RANGE_LOW <= score <= config.JUDGE_FALLBACK_RANGE_HIGH:
        verdict = await _llm_fallback_verdict(question, expected_answer, player_answer)
        final_score, damage_multiplier = _CLEAN_OVERRIDE[verdict]
    else:
        verdict = _verdict_from_score(score)
        final_score = score
        damage_multiplier = _MULTIPLIER_BY_VERDICT[verdict]

    return {
        "score": final_score,
        "damage_multiplier": damage_multiplier,
        "verdict": verdict,
        "feedback": _FEEDBACK_BY_VERDICT[verdict],
    }
