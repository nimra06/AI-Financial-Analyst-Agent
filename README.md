# AI Financial Analyst Agent

Upload monthly P&L data and get validated KPIs, forecasts, anomaly flags, and AI insights grounded in computed metrics—not guessed numbers.

**Demo / portfolio project only. Not financial advice.**

## Stack

- **Backend:** FastAPI, pandas, Prophet, OpenAI (tool-based chat)
- **Frontend:** Next.js 14, Tailwind, Recharts
- **Data:** SQLite (local) or PostgreSQL (Docker)
- **Ops:** Docker Compose, background worker, JWT / Google SSO, API keys

## Quick start (local)

**API**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-full.txt
cp .env.example .env          # set OPENAI_API_KEY, JWT_SECRET
export PYTHONPATH=app
uvicorn api.main:app --reload --port 8000
```

**UI**

```bash
cd frontend
cp .env.local.example .env.local
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Data** → upload `datasets/sample/retail_monthly_pl.csv`.

**Background jobs** (forecasts, scheduled reports):

```bash
PYTHONPATH=app python -m worker.runner
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8000` · UI: `http://localhost:3000` · Health: `/health/ready`

## Data format

| Column | Required | Notes |
|--------|----------|--------|
| `date` | Yes | Month (e.g. `2024-01-01`) |
| `revenue` | Yes | Numeric |
| `cogs`, `opex` | No | Costs |
| `category`, `amount` | No | Expense breakdown |
| `budget_revenue`, `budget_opex` | No | Budget vs actual |

Samples: `datasets/sample/`

## Deploy

### Frontend — Vercel
- **Root Directory:** `frontend` (required — not repo root)
- **Install Command:** leave empty, or use `npm install` (do **not** use `pip install`)
- **Env:** `NEXT_PUBLIC_API_URL` = `https://ai-financial-analyst-agent-production.up.railway.app`
- If build still runs `pip install`, open **Settings → General → Install Command** → clear it → redeploy

### Backend — Railway only
- **Builder:** Dockerfile → `Dockerfile.api` (see `railway.toml`)
- **Env:** `OPENAI_API_KEY`, `JWT_SECRET`; optional `DATABASE_URL` (Postgres plugin)
- **Health:** `GET /health` → `{"status":"ok"}`

## Tests

```bash
export PYTHONPATH=app && pytest
```
