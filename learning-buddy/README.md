# Gold Trading Buddy

A deliberately small, ADHD-friendly XAUUSD chart-learning companion. It offers short lessons, quick quizzes, saved learning progress, and historical OHLC chart viewing.

**Scope:** education and historical observation only. It does not generate actionable trading signals, provide financial advice, connect to a broker, or execute orders.

## Run with Docker (WSL2)

```bash
git clone https://github.com/mvallautomations/gold24-7.git
cd gold24-7/learning-buddy
docker compose up --build -d
```

Open http://localhost:8501

Stop:

```bash
docker compose down
```

Learning progress is stored in a Docker volume named `buddy-data`, so rebuilding the container does not erase it.

## Run locally without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## CSV chart practice

Upload a CSV with these column names (case-insensitive):

- `time`
- `open`
- `high`
- `low`
- `close`

Volume is optional. The chart displays up to the latest 500 valid rows.

## Included in v0.1

- 10 bite-sized beginner lessons
- ELI10 explanations, look-for lists, and common mistakes
- Four quick knowledge checks
- XP-style quiz points and lesson completion tracking
- SQLite progress persistence
- Historical OHLC candlestick chart viewer

## Next small improvements

1. Add a built-in sample dataset.
2. Add a guided chart-reading exercise with feedback.
3. Add a simple glossary and review queue.
4. Add indicator overlays only when the core learning flow feels useful.
