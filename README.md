# SkillQuest: The AI Dungeon

SkillQuest is an adaptive dungeon-crawler RPG where your knowledge in Data Structures & Algorithms (DSA) powers your character. Powered by a FastAPI backend and Google's Gemini AI, the game dynamically generates questions, evaluates answers semantically, adjusts difficulty via reinforcement learning, and routes players through a knowledge graph to strengthen weak topics.

## Folder Structure

- `backend/`: Contains the complete Python backend application.
  - `main.py`: The FastAPI application entry point.
  - `routes/`: API endpoints for the game logic and AI interactions.
    - `game.py`: Standard game flow (sessions, rooms, player stats, guilds, leaderboards).
    - `ai_real.py`: Real Gemini API endpoints for question generation, semantic answer judging, difficulty adjustment, and knowledge graph routing.
    - `ai_mock.py`: Mock endpoints for testing without the Gemini API.
  - `models/`: SQLAlchemy ORM models representing the database schema (Players, Dungeons, Submissions, etc.).
  - `schemas/`: Pydantic models for request validation and response formatting.
  - `services/`: Core logic services.
    - `game_logic.py`: Calculations for XP, damage, levels, streaks, and room clears.
    - `ai_client.py`: HTTP Client for interacting with the AI endpoints internally.
    - `knowledge_graph.py`: The DSA knowledge graph and logic for routing to weak topics based on past accuracy.
  - `db/`: Database configuration and seeding scripts.
    - `database.py`: SQLAlchemy SQLite setup.
    - `seed.py`: Populates the database with initial demo data (a seeded DSA dungeon and rooms).
  - `.env`: Environment variables configuration (including `GEMINI_API_KEY` and game balancing thresholds).
  - `requirements.txt`: Python dependencies.
  - `test_*.py`: Various test scripts for verifying E2E flows, guilds, and the Gemini integration.

## Getting Started

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Activate the virtual environment (if using the existing `venv`):
   ```powershell
   # On Windows
   .\venv\Scripts\Activate.ps1
   ```

3. Install dependencies (if setting up fresh):
   ```bash
   pip install -r requirements.txt
   ```

4. Run the server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. Explore the interactive API documentation:
   Visit `http://localhost:8000/docs` in your browser.

## AI Integration & Fallbacks

The backend leverages Google's Gemini AI via the `google-generativeai` SDK. The game is designed to be resilient—if the free-tier Gemini API quotas are exhausted (Rate Limit 429), the endpoints will gracefully fall back to generic questions and keyword-based answer judging, ensuring the game loop remains fully playable without interruption.
