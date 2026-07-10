# SkillQuest AI Services

Standalone implementation of the Person 3 AI/ML API. The game backend can call this process by setting `AI_SERVICE_URL=http://localhost:8001`.

## Run

```powershell
cd services
if (-not (Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m uvicorn main:app --reload --port 8001
```

Copy `.env.example` to `.env` and provide `GEMINI_API_KEY` for generated questions and borderline-answer adjudication. Difficulty and knowledge-graph tests run without an API key.

## Endpoints

- `POST /ai/question/generate`
- `POST /ai/answer/judge`
- `POST /ai/difficulty/next`
- `POST /ai/graph/next-topic`
