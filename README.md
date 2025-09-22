# Expense Tracker with AI Insights (Flask + SQLite)

A lightweight web app to track expenses and get simple AI insights and savings suggestions.

## Features
- Add, list, filter, and delete expenses
- Dashboard with spend by category and monthly totals (Chart.js)
- AI Insights:
  - Per-category forecast for next month (simple trend model)
  - Suggested soft caps and anomaly flags
  - Practical savings tips by category
- Uses SQLite by default; no external DB required

## Tech
- Python 3.9+
- Flask
- SQLAlchemy (ORM)
- Chart.js (via CDN)
- No heavy ML deps; uses a simple linear trend

## Quickstart

```bash
# 1) Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the app
python app.py
# Open http://127.0.0.1:5000
```

> Optional: set a custom DB or secret key
```bash
export SECRET_KEY="replace-me"
export DATABASE_URL="sqlite:///expense_tracker.db"  # default
```

## Database
Tables auto-create on first run. Data stored in `expense_tracker.db` (SQLite).

## Deploy Notes (Heroku-ish / Render)
- Use `gunicorn` if deploying behind WSGI
- Set `DATABASE_URL` appropriately for Postgres (e.g., `postgresql+psycopg2://...`)

## Troubleshooting
- If charts look empty, add some expenses first 😊
- Date format: YYYY-MM-DD
- If you change Python version, re-create the virtualenv
