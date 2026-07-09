"""
AI endpoints (P3-owned, README section 5 "AI endpoints (P3 owns)").

Thin FastAPI wrappers around services/*.py. No business logic lives here --
each route just validates the request shape and delegates.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from services.knowledge_graph import get_next_topic
from services.llm_engine import QuestionGenerationError, generate_question
from services.nlp_judge import judge_answer
from services.rl_tuner import get_next_difficulty

router = APIRouter(prefix="/ai", tags=["ai"])

Difficulty = Literal["easy", "medium", "hard"]
Verdict = Literal["correct", "partial", "incorrect"]


class AccuracyEntry(BaseModel):
    attempts: int
    correct: int
    recent_accuracy: float
    last_5_results: list[bool]


# ---- POST /ai/question/generate --------------------------------------------


class QuestionRequest(BaseModel):
    player_id: str
    topic: str
    difficulty: Difficulty
    domain: str


class QuestionResponse(BaseModel):
    question_id: str
    question: str
    expected_answer: str
    hint: str


# CALLED BY: Person 2's backend in POST /game/room/enter
@router.post("/question/generate", response_model=QuestionResponse)
async def question_generate(payload: QuestionRequest) -> QuestionResponse:
    try:
        result = await generate_question(
            topic=payload.topic, difficulty=payload.difficulty, domain=payload.domain
        )
    except QuestionGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        # Catches anything llm_engine.py's retry loop doesn't itself retry on
        # (auth errors, rate limits, network failures) -- without this, the
        # caller just sees FastAPI's bare "Internal Server Error" with no detail.
        raise HTTPException(
            status_code=500, detail=f"LLM provider error during question generation: {exc}"
        ) from exc
    return QuestionResponse(**result)


# ---- POST /ai/answer/judge --------------------------------------------------


class JudgeRequest(BaseModel):
    question_id: str
    player_answer: str
    expected_answer: str
    question: str = ""


class JudgeResponse(BaseModel):
    score: float
    damage_multiplier: float
    verdict: Verdict
    feedback: str


# CALLED BY: Person 2's backend in POST /game/answer/submit
@router.post("/answer/judge", response_model=JudgeResponse)
async def answer_judge(payload: JudgeRequest) -> JudgeResponse:
    result = await judge_answer(
        player_answer=payload.player_answer,
        expected_answer=payload.expected_answer,
        question=payload.question,
    )
    return JudgeResponse(**result)


# ---- POST /ai/difficulty/next ----------------------------------------------


class DifficultyRequest(BaseModel):
    player_id: str
    topic: str
    accuracy_history: dict[str, AccuracyEntry]


class DifficultyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    difficulty: Difficulty
    reason: str = Field(alias="_reason")


# CALLED BY: Person 2's backend in POST /game/room/enter (when requesting
# dynamic difficulty for the next question on this topic)
@router.post("/difficulty/next", response_model=DifficultyResponse)
async def difficulty_next(payload: DifficultyRequest) -> DifficultyResponse:
    accuracy_history_raw = {
        topic: entry.model_dump() for topic, entry in payload.accuracy_history.items()
    }
    result = get_next_difficulty(
        player_id=payload.player_id, topic=payload.topic, accuracy_history=accuracy_history_raw
    )
    return DifficultyResponse(difficulty=result["difficulty"], _reason=result["_reason"])


# ---- POST /ai/graph/next-topic ----------------------------------------------


class NextTopicRequest(BaseModel):
    player_id: str
    accuracy_history: dict[str, AccuracyEntry]


class NextTopicResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    next_topic: str
    weak_topics: list[str]
    unlocked_topics: list[str] = Field(alias="_unlocked_topics")
    locked_topics: list[str] = Field(alias="_locked_topics")


# CALLED BY: Person 2's backend to drive dungeon room routing/unlocks
@router.post("/graph/next-topic", response_model=NextTopicResponse)
async def graph_next_topic(payload: NextTopicRequest) -> NextTopicResponse:
    accuracy_history_raw = {
        topic: entry.model_dump() for topic, entry in payload.accuracy_history.items()
    }
    result = get_next_topic(player_id=payload.player_id, accuracy_history=accuracy_history_raw)
    return NextTopicResponse(
        next_topic=result["next_topic"],
        weak_topics=result["weak_topics"],
        _unlocked_topics=result["_unlocked_topics"],
        _locked_topics=result["_locked_topics"],
    )
