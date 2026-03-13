# CapitalGuard Algo Trader – Upstox

Capital-preserving, high-probability index options trading system. Trades only the easiest market conditions (trend continuation with engulfing confirmation). Prioritizes drawdown avoidance, consistency, and long winning streaks over aggressive returns.

**Stack:** Backend Python FastAPI | Web Next.js (React) | Mobile React Native | Upstox API | PostgreSQL + Redis.

---

## How to run

**→ [HOW-TO-RUN.md](HOW-TO-RUN.md)** — clear instructions to execute the app:

1. **First-time:** Install Python 3.11+ and Node.js 18+, then run setup (venv + `pip install`, `npm install`) once.
2. **Every time:** From project root in PowerShell run **`.\Start-All.ps1`** (or use VS Code: **Run Task → Start All**), then open **http://localhost:3000**.

Detailed install (Docker, `.env`, Upstox): **[docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md)**.

---

## Docs

| Document | Purpose |
|----------|---------|
| [docs/BRD.md](docs/BRD.md) | Business requirements, risk-first philosophy, MVP vs Phase-2 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | C4 + event model, service responsibilities, idempotency |
| [docs/INFRASTRUCTURE_DEVOPS.md](docs/INFRASTRUCTURE_DEVOPS.md) | Terraform, CI/CD, secrets, backups, cost guardrails |
| [docs/CLOUD_AND_SCHEDULE.md](docs/CLOUD_AND_SCHEDULE.md) | Deploy to cloud (Vercel + Render/Railway), run weekdays 9:15–15:30 IST only |
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

**→ Full step-by-step (copy-paste commands, what to set in `.env`): [HOW-TO-RUN.md](HOW-TO-RUN.md) — section “Clear 5-step run”.**

Short version:

1. **`.env`:** Copy `.env.example` to `.env`. Edit `.env` and set:  
   `DATABASE_URL=postgresql://capitalguard:capitalguard@localhost:5432/capitalguard`,  
   `REDIS_URL=redis://localhost:6379/0`,  
   `JWT_SECRET=` (any long random string, e.g. 32+ characters).
2. **DB + Redis:** `docker-compose up -d db redis` (Docker Desktop must be running).
3. **Backend:** In PowerShell: `cd backend` → `.\.venv\Scripts\Activate.ps1` → `pip install -e ".[dev]"` (once) → `$env:PYTHONPATH=(Get-Location).Path; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
4. **Web:** In a second PowerShell: `cd web` → `npm install` (once) → `npm run dev`.
5. **Browser:** Open http://localhost:3000.  
   (Optional mobile: `cd mobile` → `npm install` → `npx react-native start`.)

---

## CI

- **Backend:** `.github/workflows/backend.yml` – lint (ruff), unit tests (pytest), Docker build on push.

---

## License & disclaimer

Proprietary. Not financial advice. Trading involves risk. Use at your own responsibility.
