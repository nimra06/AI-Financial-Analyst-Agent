# AI Financial Analyst Agent

Enterprise-grade AI financial analysis: upload P&L data → KPIs → forecasts → anomalies → AI insights → executive reports.

> For analysis and demonstration only. Not financial advice.

## Architecture

| Layer | Stack |
|-------|--------|
| **UI (Step 7)** | Next.js 14, React, Tailwind, shadcn-style components, Recharts |
| **API** | FastAPI, Python analytics engine |
| **Legacy UI** | Streamlit (`app/streamlit_app.py`) |

## Quick start — Premium dashboard (recommended)

### 1. Backend API

```bash
cd "AI Financial Analyst Agent"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
export PYTHONPATH=app
uvicorn api.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

### 3. Try it

1. Go to **Reports** → drag & drop `datasets/sample/retail_monthly_pl.csv`
2. Explore **Overview**, **Analytics**, **AI Insights**, **Forecast**, **Anomalies**, **AI Assistant**

## Quick start — Streamlit (legacy)

```bash
source .venv/bin/activate
streamlit run app/streamlit_app.py
```

Open http://localhost:8501

## Features

| Step | Status | What it does |
|------|--------|----------------|
| 1–6 | Done | Upload, KPIs, AI summary, chat, forecast, anomalies, PDF/HTML reports |
| 7 | Done | Premium Next.js dashboard + SQLite upload history |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/upload` | Upload CSV/XLSX → full dashboard payload |
| GET | `/api/v1/sessions` | Recent uploads |
| GET | `/api/v1/sessions/{id}` | Restore session |
| POST | `/api/v1/summarize` | Executive summary (OpenAI) |
| POST | `/api/v1/forecast` | Prophet forecast |
| POST | `/api/v1/chat` | Tool-based chat |
| POST | `/api/v1/why-panel` | Explainability rows |

## UI design (Step 7)

- Dark-only fintech aesthetic (`#0B0F19` background)
- Left sidebar + top header
- KPI cards, Recharts analytics, AI insight cards
- Drag-and-drop upload, chat panel, sessions table
- Subtle glassmorphism, Inter typography, minimal motion

## Data contract

| Column | Required | Description |
|--------|----------|-------------|
| `date` | Yes | Month |
| `revenue` | Yes* | Revenue |
| `cogs`, `opex` | No | Costs |
| `category`, `amount` | No | Expense breakdown |

Sample files in `datasets/sample/`.

## Tests

```bash
pytest
```

## Project structure

```
app/                    # Python backend
  api/main.py           # FastAPI
  analytics/            # ingest, KPIs, charts, forecast, anomalies
  llm/                   # OpenAI agents
  reports/              # HTML/PDF reports
  db/                   # SQLite sessions
frontend/               # Next.js dashboard (Step 7)
  src/components/       # UI modules
datasets/sample/
tests/
```

## Roadmap

See [roadmap.txt](roadmap.txt). **Next: Step 8** — deploy with Docker, rate limits, hardening.
