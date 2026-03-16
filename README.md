# CapitalGuard Algo Trader – Upstox

Capital-preserving, high-probability index options trading system. **Final strategy:** S/R + CPR + engulfing (5m/2m); time 9:20–14:45 IST; no 15m EMA bias. Prioritizes drawdown avoidance, consistency, and long winning streaks over aggressive returns.

**Stack:** Backend Python FastAPI | Web Next.js (React) | Mobile React Native | Upstox API | PostgreSQL + Redis.

---

## How to run

**→ [HOW-TO-RUN.md](HOW-TO-RUN.md)** — clear instructions to execute the app.

**Dashboard shows “Backend not reachable”?** → **[BACKEND-NOT-REACHABLE-FIX.md](BACKEND-NOT-REACHABLE-FIX.md)** — checklist to fix it.

1. **First-time:** Install Python 3.11+ and Node.js 18+, then run setup (venv + `pip install`, `npm install`) once.
2. **Every time:** From project root in PowerShell run **`.\Start-All.ps1`** (or use VS Code: **Run Task → Start All**), then open **http://localhost:3000**. Keep both backend and web terminals open.

**Host in cloud (Vercel + Render):** **[HOST-IN-CLOUD.md](HOST-IN-CLOUD.md)** — step-by-step with copy-paste commands and env vars.

Detailed install (Docker, `.env`, Upstox): **[docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md)**.

---

## Docs

| Document | Purpose |
|----------|---------|
| [docs/FINAL_STRATEGY_HIGH_PROBABILITY.md](docs/FINAL_STRATEGY_HIGH_PROBABILITY.md) | **Final signal strategy:** time 9:20–14:45 IST, S/R + CPR + engulfing, no EMA bias; entry/SL/book profit |
| [docs/STRATEGY_IMPLEMENTATION_FILES.md](docs/STRATEGY_IMPLEMENTATION_FILES.md) | **Strategy files index:** all code and docs for buy, SL, book profit |
| [docs/BRD.md](docs/BRD.md) | Business requirements, risk-first philosophy, MVP vs Phase-2 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | C4 + event model, service responsibilities, idempotency |
| [docs/INFRASTRUCTURE_DEVOPS.md](docs/INFRASTRUCTURE_DEVOPS.md) | Terraform, CI/CD, secrets, backups, cost guardrails |
| [docs/CLOUD_AND_SCHEDULE.md](docs/CLOUD_AND_SCHEDULE.md) | Deploy to cloud (Vercel + Render/Railway); **start and monitor from mobile + laptop** (one URL); weekdays 9:15–15:30 IST |
| [docs/DELIVERY_PLAN.md](docs/DELIVERY_PLAN.md) | MVP roadmap, 8–10 sprints, epics/stories, RAID |

---

## Strategy (final – high-probability signals)

- **Time:** **09:20–14:45 IST** (9:20 AM to 2:45 PM). No 15m EMA bias (Option B).
- **CPR:** Price **inside** CPR band → no trade. **CPR bottom bounce** → BUY; **CPR top rejection** → SELL.
- **BUY:** Support bounce (5m), CPR bottom bounce (5m), or Bullish engulfing + 2m entry.
- **SELL:** Resistance rejection (5m), CPR top rejection (5m), or Bearish engulfing + 2m entry.
- **Risk:** Max 3 trades/day; daily loss stop; 1 lot; no scaling.

**Full spec:** [docs/FINAL_STRATEGY_HIGH_PROBABILITY.md](docs/FINAL_STRATEGY_HIGH_PROBABILITY.md).

### Daily trade logging & reports

- Every order placed/closed is logged as CSV under `backend/app/logs/trades/trades-YYYY-MM-DD.csv` (OPEN/CLOSE events with expected SL/target and exit reason).
- Use `trade_logger.send_daily_trade_report_email()` (e.g. from a small scheduled job) to receive an **end-of-day email** summarizing trades, with the full log in the body.

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
