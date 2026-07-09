"""
LLM Question Engine (P3-owned, README section 4.1).

NO P2 DEPENDENCY. topic/difficulty/domain are supplied directly by the
caller (eventually Person 2's POST /game/room/enter handler, but fully
testable solo by passing these three strings ourselves).
"""

import json
import re
import uuid

from google import genai
from google.genai import types

import config

MIN_EXPECTED_ANSWER_LENGTH = 30
MAX_ATTEMPTS = 3

_client = genai.Client(api_key=config.GEMINI_API_KEY)

PROMPT_TEMPLATE = """You are a dungeon monster in an educational RPG.
Topic: {topic}
Difficulty: {difficulty}
Subject domain: {domain}

Generate a single exam-quality question for a student fighting you.
Respond in JSON only, no preamble:
{{
  "question": "...",
  "expected_answer": "...",
  "hint": "..."
}}"""


class QuestionGenerationError(Exception):
    """Raised when the LLM fails to produce a valid question after MAX_ATTEMPTS retries."""


def _extract_json(raw_text: str) -> dict:
    """
    Pulls a JSON object out of the LLM's raw text response.

    Gemini is instructed to respond JSON-only, but models sometimes wrap
    output in markdown code fences anyway -- strip those before parsing.
    Raises json.JSONDecodeError / ValueError on malformed input, which the
    caller's retry loop catches.
    """
    text = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


async def generate_question(topic: str, difficulty: str, domain: str) -> dict:
    """
    Generate a single unique question for a fight.

    Inputs:
        topic: str -- exact topic name (e.g. "binary_search"). Must match
            one of the 11 README topic names, but this function does not
            validate that itself; routes/ai.py is responsible for that.
        difficulty: str -- "easy" | "medium" | "hard".
        domain: str -- subject domain, e.g. "Data Structures & Algorithms".

    Output:
        dict matching the POST /ai/question/generate response contract:
        { question_id, question, expected_answer, hint }

    P2 dependency: NONE. All three inputs are supplied directly by the
    caller. Fully testable solo (see tests/test_llm_engine.py).

    Raises:
        QuestionGenerationError if the LLM fails to return valid JSON with
        a sufficiently detailed expected_answer after MAX_ATTEMPTS retries.
    """
    prompt = PROMPT_TEMPLATE.format(topic=topic, difficulty=difficulty, domain=domain)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await _client.aio.models.generate_content(
                model=config.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.9,
                ),
            )
            raw_text = response.text
            if not raw_text or not raw_text.strip():
                # Gemini returns text=None/"" instead of raising when a response
                # is blocked by safety filters or hits a non-STOP finish_reason
                # (observed empirically: empty string, not just None).
                finish_reason = response.candidates[0].finish_reason if response.candidates else None
                raise ValueError(f"Gemini returned no text (finish_reason={finish_reason!r})")
            parsed = _extract_json(raw_text)

            question = parsed["question"]
            expected_answer = parsed["expected_answer"]
            hint = parsed["hint"]

            if len(expected_answer) < MIN_EXPECTED_ANSWER_LENGTH:
                raise ValueError(
                    f"expected_answer too short ({len(expected_answer)} chars); "
                    f"NLP judge needs >= {MIN_EXPECTED_ANSWER_LENGTH} chars to score against"
                )

            return {
                "question_id": str(uuid.uuid4()),
                "question": question,
                "expected_answer": expected_answer,
                "hint": hint,
            }
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            continue

    raise QuestionGenerationError(
        f"Failed to generate a valid question for topic={topic!r} "
        f"difficulty={difficulty!r} after {MAX_ATTEMPTS} attempts: {last_error}"
    )
