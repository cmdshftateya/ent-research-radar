# ENT Research Tool

Mid-century inspired dashboard plus data pipeline for ENT faculty discovery and outreach.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run API (FastAPI)

```bash
uvicorn backend.app.main:app --reload
```

API base: `http://localhost:8000`

## Seed sample data (offline-friendly)

```bash
ENT_OFFLINE=true python cli/refresh.py seed-sample
```

## Refresh live data (scrape + publications)

```bash
export SEMANTIC_SCHOLAR_API_KEY=your_key   # optional but recommended
python cli/refresh.py refresh
```

Set `ENT_OFFLINE=true` to avoid network calls; with it set, refresh loads only sample data.

## Frontend

Open `frontend/index.html` in your browser. It expects the API at `http://localhost:8000`. Use the floating “Draft email” button to open the sidebar; copy uses the Clipboard API.

## Scheduler

See `docs/scheduler.md` for a weekly Monday run via launchd/cron. The CLI entrypoint is `python cli/refresh.py refresh`.
