"""
SkillQuest Backend — FastAPI entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from db.database import engine, Base, ensure_columns

# Import all models so tables are registered with Base.metadata
from models.player import Player
from models.accuracy_history import AccuracyHistory
from models.question import Question
from models.submission import AnswerSubmission
from models.guild import Guild
from models.dungeon import Dungeon, Room
from models.session import GameSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup, seed demo data."""
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")

    # Phase 2/3 columns added to an existing players table after the demo DB
    # was first created -- create_all() above never alters existing tables.
    ensure_columns("players", [
        ("hero_id", "TEXT"),
        ("pending_xp_multiplier", "REAL DEFAULT 1.0"),
        ("pending_verdict_boost", "BOOLEAN DEFAULT 0"),
        ("pending_force_correct", "BOOLEAN DEFAULT 0"),
        ("powerup_window_start", "TEXT"),
        ("powerup_uses_this_window", "INTEGER DEFAULT 0"),
    ])
    ensure_columns("accuracy_history", [
        ("mastered", "BOOLEAN DEFAULT 0"),
    ])

    # Auto-seed the demo dungeon
    from db.seed import seed_database
    seed_database()

    yield


app = FastAPI(
    title="SkillQuest API",
    description="The AI Dungeon — adaptive learning RPG backend",
    version="1.0.0",
    lifespan=lifespan,
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        # :3001 included too -- `next dev` silently falls back to it whenever
        # another process (often a stale dev server from a previous session)
        # is still squatting :3000, and a CORS-rejected preflight ("Could not
        # reach the backend") is a much more confusing failure than just
        # trusting both ports up front.
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    ).split(",")
    if origin.strip()
]

# Credentialed browser requests require explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        print(f"[{request.method}] {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)")
        return response


app.add_middleware(RequestLoggingMiddleware)

# Import and include routers
from routes.game import router as game_router
from routes.ai_real import router as ai_router

app.include_router(game_router)
app.include_router(ai_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "app": "SkillQuest: The AI Dungeon",
        "version": "1.0.0",
        "docs": "/docs",
    }
