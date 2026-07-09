"""
FastAPI app entry point for the AI/ML services layer (P3-owned).

Person 2 mounts/calls into this from their own server-side flows; this
process can also be run standalone for local development:

    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config  # noqa: F401  -- importing triggers .env load + key validation
from routes.ai import router as ai_router

app = FastAPI(title="SkillQuest AI Services", version="1.0.0")

# TODO INTEGRATION: Lock down allowed_origins to Person 2's server URL when
# merging. Currently open for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
