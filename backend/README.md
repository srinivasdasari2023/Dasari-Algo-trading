# CapitalGuard Backend

Python FastAPI. Strategy engine (Trend-Continuation Capital Preserver), pattern detector (engulfing only), risk engine, Upstox order manager. Event-driven; PostgreSQL + Redis.

## Setup

```bash
pip install -e ".[dev]"
cp ../.env.example ../.env   # then edit .env
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -v tests/
ruff check app tests
```

## Structure

- `app/main.py` – FastAPI app
- `app/core/` – config, (future: DB, auth)
- `app/api/` – REST routes: auth, market, signals, risk, orders, dashboard, audit
- `app/services/` – strategy_engine, pattern_detector, market_context, risk_engine, order_manager
