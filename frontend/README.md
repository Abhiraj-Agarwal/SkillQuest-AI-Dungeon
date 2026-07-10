# CodeCrypt — Frontend

Next.js 15 (App Router) frontend for **CodeCrypt: The AI Dungeon**. Fully playable right now against
a built-in mock backend — no FastAPI server required to demo it.

## Run it

```powershell
npm install
if (-not (Test-Path .env.local)) { Copy-Item .env.local.example .env.local }
npm run dev
```

Open http://localhost:3000. Register any character name (mock mode auto-creates the player).

## Switching from mock to the real backend

Edit `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=false
```

That's it — every API call in the app goes through `lib/api/client.js`, which branches on
`USE_MOCK`. No component, page, or store talks to `fetch` directly, so nothing else needs to change.

## What's built

- **Player identity** — create/enter/logout pages, locally restored player session, and guarded routes
  via `lib/useRequireAuth.js`. This hackathon build does not implement password authentication.
- **DungeonMap** (`/dungeon`) — the 11-topic knowledge graph rendered as a literal level-select map:
  stone tiles connected by glowing prerequisite lines. Locked/unlocked/weak/mastered styling driven
  by live accuracy data. Boss room gates open once every topic exceeds 65% recent accuracy.
- **Combat** (`/combat/[roomId]`) — free-text answer box, segmented pixel HP bars for player + enemy,
  floating damage/XP numbers, hint tokens, multi-question fights against one enemy until it's defeated.
- **BossFight** (`/boss/[dungeonId]`) — same combat loop, bigger HP pool, questions rotate across all
  topics.
- **StatSheet** (`/stats`) — per-topic accuracy mapped to RPG stats (see `lib/statMap.js`).
- **Guild** (`/guild`) — join a raid party, see member topic-lanes and shared boss HP.
- **Leaderboard** (`/leaderboard`) — polls every 5s, highlights your row.
- **AI Core dashboard** (`/dashboard`) — the judge-facing panel: live knowledge graph (React Flow,
  same layout function as the dungeon map on purpose), RL difficulty history and NLP score history
  charts (Recharts). Polls every 6s.

## Folder structure

```
app/                  routes (App Router) — one folder per page
components/           game UI (HealthBar, XPBar, HintToken, MLDashboard, NavBar, DamageNumber)
components/ui/        pixel design system primitives (Panel, Button, Input, Badge)
lib/api/client.js      ← the ONLY file that calls fetch
lib/mock/mockData.js   in-memory mock backend, mirrors the real contract exactly
lib/config.js          env-driven config (API URL, mock toggle)
lib/statMap.js          topic ↔ RPG stat names, mirrors backend TOPIC_GRAPH
lib/graphLayout.js      shared layout math for DungeonMap + MLDashboard's graph
store/                  Zustand: useAuthStore, useGameStore
```

## Known gaps / questions for the team

- Mock combat invents its own HP/respawn rules (player HP persists across rooms, retreat resets it).
  These are mock-only conveniences in `lib/mock/mockData.js` — the real backend can implement
  HP/death however P2 prefers; the frontend only needs `player_hp_after` / `enemy_hp_after` back from
  `/game/answer/submit`.
- See `CodeCrypt_Frontend_Spec.md` (shared separately) for the full API contract this was built against.
