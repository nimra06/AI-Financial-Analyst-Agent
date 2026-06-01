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
- **Root Directory:** `frontend`
- **Env:** `NEXT_PUBLIC_API_URL` = your Railway API URL

### Backend — Railway (recommended)
Railpack often mis-detects this repo (Django/gunicorn). Use **Docker** instead.

1. Push `railway.toml` + `Dockerfile.api` (in this repo).
2. Railway → **New Project** → **Deploy from GitHub** → this repo.
3. **Settings → Build:** Builder = **Dockerfile**, path = **`Dockerfile.api`** (or rely on `railway.toml`).
4. **Variables:** `OPENAI_API_KEY`, `JWT_SECRET`; optional `DATABASE_URL` (add Railway Postgres plugin).
5. **Networking** → generate domain → e.g. `https://xxx.up.railway.app`
6. Set Vercel `NEXT_PUBLIC_API_URL` to that URL (no trailing slash).

**Health check:** `GET /health` should return `{"status":"ok"}`.

## Tests

```bash
export PYTHONPATH=app && pytest
```
