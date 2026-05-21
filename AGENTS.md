# AGENTS.md

## Repo Structure

- `backend/` — FastAPI (Python), SQLAlchemy + aiosqlite, pandas/numpy for financial calc
- `frontend/` — React 18 + TypeScript, Vite, Recharts
- `openspec/` — change management artifacts
- No root `package.json`; each package is independent

## Commands

### Backend
```powershell
cd backend
pip install -r requirements.txt
pytest                              # run all tests
pytest backend/tests/test_foo.py    # single test file
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # dev server
```

### Frontend
```powershell
cd frontend
npm install
npm run dev          # Vite dev server
npm run build        # tsc && vite build
npm run lint
npm run test         # vitest run
```

## Key Conventions

- Backend entrypoint: `backend.main:app` (FastAPI app object, not a class)
- Frontend entrypoint: `frontend/src/App.tsx`
- CORS is open (`allow_origins=["*"]`)
- DB: `data/etf_database.db` (SQLite); created automatically on first startup
- Backend uses sync SQLAlchemy sessions (`with get_session() as session:` pattern)
- OpenCode MCP browser plugin configured in `opencode.json`