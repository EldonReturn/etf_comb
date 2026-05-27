# AGENTS.md

## 语言要求

1. 全程思考过程必须使用中文（需求分析、逻辑拆解、方案选择、步骤推导等所有内部推理环节）；
2. 最终输出的所有回答内容必须全部使用中文（文字解释、代码注释、步骤说明等），仅代码语法本身的英文关键词除外。

## Repo Structure

- `backend/` — FastAPI (Python), SQLAlchemy + aiosqlite, pandas/numpy for financial calc
- `frontend/` — React 18 + TypeScript, Vite, Recharts, vitest
- `openspec/` — change management (spec-driven workflow, see `openspec/config.yaml`)
- `data/` — SQLite DB lives here (`etf_database.db`), gitignored
- No root `package.json`; each package is independent

## Commands

All commands run from repo root unless noted.

### Backend
```powershell
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000   # dev server (API docs at /docs)

pytest                              # run all tests (verbose, short tb — see pytest.ini)
pytest backend/tests/test_foo.py    # single test file
```

### Frontend
```powershell
cd frontend
npm install
npm run dev          # Vite dev server (port 3000, proxies /api → localhost:8000)
npm run build        # tsc && vite build
npm run lint         # eslint (ts,tsx) with --max-warnings 0
npm run test         # vitest run (jsdom, @testing-library/jest-dom)
```

## Key Conventions & Gotchas

### Auth (dual system)
- **Frontend auth** (`/api/auth/*`): cookie-based session, password from `FRONTEND_PASSWORD` env var (hash: `FRONTEND_PASSWORD_HASH`). 1-hour session expiry.
- **Admin auth** (`/api/admin/*`): cookie-based session, password from `ADMIN_PASSWORD` env var (defaults to `admin123`).
- Every API endpoint (except `/`, `/api/auth/login`, `/api/auth/check`, `/api/admin/login`) requires `session_id: str = Depends(require_auth)`.
- `backend/.env` loaded via `dotenv` at module level in `main.py` and `routes/auth.py`.

### Database
- DB file: `data/etf_database.db` — created automatically on first startup. Gitignored.
- **Sync SQLAlchemy only**: use `with get_session() as session:` context manager. Auto-commits on success, rollback on exception.
- Engine singleton: `check_same_thread=False` (required for SQLite with FastAPI).
- Models: `ETFInfo`, `ETFNavHistory`, `TradeDate` (all in `backend/db/models.py`).

### Python Import Style
- **Always use full `backend.` prefix** for internal imports: `from backend.services import ...`, `from backend.db import ...`.
- Run everything from repo root (not from inside `backend/`).

### Testing
- Tests in `backend/tests/` use **standalone algorithm implementations** — they do NOT import from `backend/services/`. This is intentional.
- `pytest.ini` at repo root: `testpaths = backend/tests`, `addopts = -v --tb=short`.
- Frontend: `vitest` + `jsdom` + `@testing-library/jest-dom` (setup in `setupTests.ts`).

### Frontend State
- `localStorage` keys prefixed `etf_comb_` for persistence (weights, portfolios, settings).
- Hash-based routing: `#admin` → admin panel. Default hash → main app.
- Auth gating: `FrontendLogin` shown if no valid session cookie. Session checked via `GET /api/auth/status`.
- Vite proxies `/api` → `http://localhost:8000`.

### Data Sources
- `akshare` — trade calendar sync (`POST /api/admin/trade_dates/sync`)
- `tickflow` — ETF list + NAV history sync (`POST /api/admin/sync`)
- ETF codes use format `XXXXXX.SH` or `XXXXXX.SZ` (e.g., `510310.SH`).

### Financial Constants
- Risk-free rate: 3% (`RISK_FREE_RATE = 0.03`)
- Trading days/year: 252 (`TRADING_DAYS_PER_YEAR = 252`)
- Default benchmark: `510310.SH`

### OpenSpec
- Config: `openspec/config.yaml` — `schema: spec-driven`
- Changes live in `openspec/changes/`, specs in `openspec/specs/`.
- Project-specific skills available: `openspec-*` commands.
