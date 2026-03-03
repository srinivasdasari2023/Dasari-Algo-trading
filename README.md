# CapitalGuard Algo Trader – Upstox

Capital-preserving, high-probability index options trading system. Trades only the easiest market conditions (trend continuation with engulfing confirmation). Prioritizes drawdown avoidance, consistency, and long winning streaks over aggressive returns.

**Stack:** Backend Python FastAPI | Web Next.js (React) | Mobile React Native | Upstox API | PostgreSQL + Redis.

---

## Install and run

**→ See [docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md)** for step-by-step instructions (prerequisites, `.env` setup, Docker for DB/Redis, backend, web, optional mobile).

---

## Docs

| Document | Purpose |
|----------|---------|
| [docs/BRD.md](docs/BRD.md) | Business requirements, risk-first philosophy, MVP vs Phase-2 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | C4 + event model, service responsibilities, idempotency |
| [docs/INFRASTRUCTURE_DEVOPS.md](docs/INFRASTRUCTURE_DEVOPS.md) | Terraform, CI/CD, secrets, backups, cost guardrails |
| [docs/DELIVERY_PLAN.md](docs/DELIVERY_PLAN.md) | MVP roadmap, 8–10 sprints, epics/stories, RAID |

---

## Strategy (non-negotiable)

- **Bias:** 15-min EMA20 > EMA200 → BUY only; EMA20 < EMA200 → SELL only; else NO TRADE.
- **Time:** 09:20–10:30, 11:15–12:30; entry cutoff 12:30; auto square-off 15:15.
- **CPR:** Price inside CPR band → no trade.
- **Pattern:** Bullish Engulfing (BUY), Bearish Engulfing (SELL) only.
- **Risk:** Max 3 trades/day; 1 loss → stop for the day; 1 lot only; no scaling.

---

## Local dev (summary)

1. Copy `.env.example` to `.env` and set `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET` (see [docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md)).
2. Start DB + Redis: `docker-compose up -d db redis`
3. Backend: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload`
4. Web: `cd web && npm install && npm run dev`
5. Optional mobile: `cd mobile && npm install && npx react-native start`

---

## CI

- **Backend:** `.github/workflows/backend.yml` – lint (ruff), unit tests (pytest), Docker build on push.

---

## License & disclaimer

Proprietary. Not financial advice. Trading involves risk. Use at your own responsibility.
