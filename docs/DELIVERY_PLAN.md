# Delivery Plan – CapitalGuard Algo Trader

**MVP-Focused Roadmap | 8–10 Sprints | Epics → Stories → Tasks**

---

## 1. MVP Scope (Phase 1)

- Upstox OAuth + market data (NIFTY, SENSEX; 15/5/2 min).  
- Trend-Continuation Capital Preserver (bias, time, CPR, engulfing, entry sequence, option filters).  
- Risk engine (max 3 trades/day, 1-loss stop, 1 lot, square-off 15:15).  
- Manual + Semi-auto modes.  
- Web dashboard (market context, signal panel, positions, history).  
- PostgreSQL + Redis; event-driven backend; audit log; RBAC.

---

## 2. Sprint Cadence & Duration

- **Sprint length**: 2 weeks.  
- **Total**: 8–10 sprints for MVP.  
- **DoR (Definition of Ready)**: Story has clear acceptance criteria; dependencies identified; design/API agreed where needed.  
- **DoD (Definition of Done)**: Code merged; tests passing; docs/runbook updated; no known P0/P1 bugs.

---

## 3. Epic → Story → Task Outline

### Epic 1: Foundation & Infra (Sprints 1–2)

| Story | Tasks |
|-------|--------|
| 1.1 Repo, lint, CI (backend + web) | Create repo structure; add ruff/pytest; GitHub Actions for test + lint; .env.example. |
| 1.2 Docker local dev | Docker Compose: API, PostgreSQL, Redis; health checks; readme. |
| 1.3 Terraform skeleton | Modules: network, DB, Redis, secrets refs; dev env only. |
| 1.4 Auth & RBAC skeleton | JWT/session; Trader/Admin roles; guard on API. |

### Epic 2: Upstox Integration (Sprint 2–3)

| Story | Tasks |
|-------|--------|
| 2.1 Upstox OAuth | OAuth flow; token refresh; store in DB/vault; no hardcoded secrets. |
| 2.2 Market data client | Fetch 15/5/2 min candles for NIFTY, SENSEX; handle rate limits. |
| 2.3 Candle storage & EMAs | Persist candles; compute EMA20/200 for 15m; EMA20 for 5m/2m. |
| 2.4 CPR calculation | CPR levels from 15m (or defined method); expose to signal service. |

### Epic 3: Strategy Engine (Sprints 3–5)

| Story | Tasks |
|-------|--------|
| 3.1 Market bias | 15m EMA20 vs EMA200 → BUY/SELL/NO_TRADE; deterministic. |
| 3.2 Time filter | 09:20–10:30, 11:15–12:30; entry cutoff 12:30; unit tests. |
| 3.3 CPR filter | If price inside CPR → no trade; integrate with bias. |
| 3.4 Engulfing detector | Bullish/Bearish Engulfing only; 5m strong candle; unit tests. |
| 3.5 Entry sequence | 2m pullback + next close above/below + 2m close vs EMA20; tests. |
| 3.6 Option filter | Premium bands (NIFTY 180–220, SENSEX 480–520); ATM; spread ≤5%; volume spike. |
| 3.7 Signal service API | Evaluate on 2m close; return signal + reason + risk checklist. |

### Epic 4: Risk Engine (Sprints 4–5)

| Story | Tasks |
|-------|--------|
| 4.1 Daily limits | Max 3 trades; 1 loss → stop day; Redis/DB counters. |
| 4.2 Square-off | 15:15 auto square-off; idempotent; audit. |
| 4.3 Risk service API | Check signal against limits; return allowed/reason. |
| 4.4 Integration with signal | Signal → risk check → allow/reject; event/command flow. |

### Epic 5: Order Management (Sprints 5–6)

| Story | Tasks |
|-------|--------|
| 5.1 Upstox order API client | Place order, SL; map instrument_key; error handling. |
| 5.2 Idempotency | Idempotency key per place-order; Redis + DB; no duplicate orders. |
| 5.3 Order service API | Place order command; persist OrderPlaced; link to signal. |
| 5.4 Semi-auto flow | On allowed signal, place entry + SL when mode = SEMI_AUTO. |

### Epic 6: Dashboard & Modes (Sprints 6–8)

| Story | Tasks |
|-------|--------|
| 6.1 Market context view | Live index, EMA20/200, CPR, market bias. |
| 6.2 Signal panel | Signal status, reason, time window, risk checklist. |
| 6.3 Open positions | Symbol, entry, live P&L, SL/trail state. |
| 6.4 History | Signal history, trade outcomes, rule violations. |
| 6.5 Mode switch | MANUAL / SEMI_AUTO; consent modal; audit log. |
| 6.6 WebSocket | Push updates for prices, signals, positions. |

### Epic 7: Audit & Hardening (Sprints 7–8)

| Story | Tasks |
|-------|--------|
| 7.1 Audit log | Every signal, order, mode change; queryable; retention. |
| 7.2 Observability | Structured logs; metrics (signals, orders, errors); alerts. |
| 7.3 Runbooks | Broker down, order failure, daily loss stop, square-off failure. |

### Epic 8: Deploy & Release (Sprints 8–10)

| Story | Tasks |
|-------|--------|
| 8.1 Staging deploy | CI/CD to staging; smoke tests. |
| 8.2 Prod deploy | Tag-based or approval-based deploy; rollback procedure. |
| 8.3 Documentation | Runbook, env setup, API summary; no marketing. |

---

## 4. RAID Log

| Type | Item | Mitigation / Owner |
|------|------|--------------------|
| **R** | Upstox API rate limits or downtime | Circuit breaker; “no trade” fallback; monitor; runbook. |
| **R** | Incorrect EMA/CPR due to data lag | Validate pipeline; reconcile; alert on anomaly. |
| **A** | Scope creep (extra patterns, brokers) | Strict DoR; BRD out-of-scope section; PM sign-off. |
| **I** | Dependency on single dev for strategy logic | Document rules; unit tests; pair review. |
| **D** | Delayed delivery due to broker docs | Early spike on Upstox; mock server for parallel work. |

---

*Document owner: Engineering Delivery Lead. Update per sprint.*
