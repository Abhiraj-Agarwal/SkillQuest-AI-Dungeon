# SkillQuest: AI Dungeon

An educational RPG where students fight dungeon monsters by answering DSA questions. Adaptive difficulty, NLP answer judging, and a live knowledge graph make every run feel different.

---

## Team Structure

### Person 1 — Frontend (The Experience Layer)

Owns everything the judge sees and touches. Pages: DungeonMap, Combat, StatSheet, BossFight, Guild, Leaderboard. Components: HealthBar, XPBar, HintToken, MLDashboard. All backend communication goes through a single `api/client.js` file — no component calls `fetch` directly. Builds against mock data from Day 1; real endpoints are a one-line swap per call when P2 publishes them.

**Stack:** React + Vite, React Router

---

### Person 2 — Backend (The Glue Layer)

Owns the FastAPI server, SQLite database, all game logic, and the API contracts that govern how the team communicates. Publishes the contract document on Day 1 before anyone else writes a meaningful line of code. Core endpoints: session start, dungeon structure, room entry (calls P3 for difficulty + question), answer submission (calls P3 to judge, writes AccuracyHistory), player stats, guild raid, leaderboard. The AccuracyHistory write on every submission is the single most critical database operation in the project — P3's RL tuner reads it from Day 3 onward.

**Stack:** FastAPI, SQLAlchemy, SQLite

---

### Person 3 — AI/ML (The Intelligence Layer)

Owns four endpoints under `/ai/`. Never touches the database or game logic directly — P2 is the customer, these are vendor services. Deliverables: `POST /ai/question/generate` (LLM prompt with retry and JSON validation), `POST /ai/answer/judge` (sentence-transformer cosine similarity with LLM fallback on borderline scores), `POST /ai/difficulty/next` (threshold-based RL tuner, epsilon-greedy bandit as a Day 5 upgrade), `POST /ai/graph/next-topic` (prerequisite-aware topic routing), and `GET /ai/dashboard/{player_id}` (aggregated judge demo panel). Critical dependency: P2 must confirm AccuracyHistory writes are live by end of Day 2.

**Stack:** FastAPI, google-genai, sentence-transformers (all-MiniLM-L6-v2)

---

## Repo Layout

```
SkillQuest-AI-Dungeon/
├── frontend/        Person 1
├── backend/         Person 2
├── services/        Person 3
└── README.md
```

---

## API Contract (published by P2 on Day 1)

All contracts live in `backend/contracts/`. No one builds against an undocumented endpoint.
