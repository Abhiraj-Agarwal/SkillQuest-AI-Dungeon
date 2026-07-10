# SkillQuest: The AI Dungeon

SkillQuest is an adaptive educational dungeon crawler where players learn Data Structures and Algorithms by fighting monsters with correct answers. The game combines a Next.js interface, a FastAPI game server, SQLite persistence, generated questions, semantic answer judging, adaptive difficulty, and knowledge-graph routing.

## Repository Layout

```text
SkillQuest-AI-Dungeon/
|-- frontend/   Next.js player experience and judge dashboard
|-- backend/    FastAPI game API, SQLite models, game logic, and seed data
|-- services/   Standalone AI/ML service implementation
`-- README.md
```

## Team Ownership

### Person 1: Frontend

Owns the dungeon map, combat and boss fights, character stats, guild, leaderboard, and ML dashboard. All browser-to-server communication is centralized in `frontend/lib/api/client.js`; the UI can run against mock data while backend integration is unavailable.

**Stack:** Next.js 15, React 19, Tailwind CSS, Zustand, TanStack Query

### Person 2: Backend

Owns the FastAPI game server, SQLite database, API contracts, game rules, demo seed data, guilds, leaderboards, and the critical accuracy-history update performed after every answer submission.

**Stack:** FastAPI, SQLAlchemy, SQLite

### Person 3: AI/ML

Owns question generation, semantic answer judging, adaptive difficulty, and knowledge-graph topic routing under `/ai/`. These services consume request data supplied by the game server and do not own game state or database writes.

**Stack:** FastAPI, Google Gemini, sentence-transformers

## Run Locally

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`. It uses mock data by default. Copy `frontend/.env.local.example` to `frontend/.env.local` and set `NEXT_PUBLIC_USE_MOCK=false` to use the game API.

### Backend

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Copy `backend/.env.example` to `backend/.env` before enabling real AI. Keep `USE_MOCK_AI=true` for a local run without a Gemini API key. API documentation is available at `http://localhost:8000/docs`.

## Core API

- `POST /game/session/start`
- `GET /game/dungeon/{dungeon_id}`
- `POST /game/room/enter`
- `POST /game/answer/submit`
- `GET /game/player/{player_id}`
- `POST /game/guild/raid/join`
- `GET /game/leaderboard`
- `POST /ai/question/generate`
- `POST /ai/answer/judge`
- `POST /ai/difficulty/next`
- `POST /ai/graph/next-topic`
- `GET /ai/dashboard/{player_id}`
