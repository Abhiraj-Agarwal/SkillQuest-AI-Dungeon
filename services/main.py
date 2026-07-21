"""
FastAPI app entry point for the AI/ML services layer (P3-owned).

Person 2 mounts/calls into this from their own server-side flows; this
process can also be run standalone for local development:

    uvicorn main:app --reload --port 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config  # noqa: F401  -- load environment configuration before routes
from routes.ai import router as ai_router
from services.nlp_judge import warm_up


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pay the SentenceTransformer model-load cost once at startup instead of
    # on the first player's answer submission.
    await warm_up()
    yield


app = FastAPI(title="SkillQuest AI Services", version="1.0.0", lifespan=lifespan)

# This service is only ever called server-to-server (by backend/services/ai_client.py
# over httpx), never from a browser, so there is no session/cookie to carry --
# allow_credentials=True served no purpose here and, combined with a wildcard
# origin, is a combination browsers reject outright anyway.
# TODO INTEGRATION: Lock down allowed_origins to Person 2's server URL when
# merging. Currently open for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)


@app.get("/")
async def root() -> dict:
    return {"message": "SkillQuest AI layer is running"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "services": ["question", "judge", "tuner", "graph"]}
