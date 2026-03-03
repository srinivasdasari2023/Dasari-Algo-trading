# Business Requirements Document (BRD)
## CapitalGuard Algo Trader – Upstox

**Version:** 1.0  
**Status:** Authoritative  
**Audience:** Product, Engineering, Risk, CTO

---

## 1. Executive Summary

CapitalGuard Algo Trader is a **capital-preserving**, **high-probability** index options trading system for Upstox. It trades only the easiest market conditions (trend continuation with engulfing confirmation), with **drawdown avoidance** and **consistency** ranked above aggressive returns. The system is deterministic, low-frequency, and supports manual, semi-automated, and fully automated execution with strict risk controls and full auditability.

---

## 2. Risk-First Philosophy

| Principle | Implication |
|-----------|-------------|
| **Capital preservation is #1** | No trade is taken if it violates daily loss limit, time window, or market bias. One loss → stop trading for the day. |
| **Fewer trades is a feature** | Time filters, CPR chop filter, and single-pattern (engulfing) focus reduce noise. Target: high win rate over high frequency. |
| **Determinism** | Same inputs (price, EMAs, CPR, time) always yield same signal. No ML black boxes; rules are auditable. |
| **Execution safety** | Idempotent order flows, position limits (1 lot), no scaling/doubling, auto square-off at 15:15. |
| **Explicit consent** | Mode switch to semi-auto or full-auto requires user confirmation and is logged. |

---

## 3. Functional Requirements

### 3.1 User & Access

- **FR-U1** Role-Based Access: Trader (signals, positions, history), Admin (risk params, schedules, user management, audit).
- **FR-U2** Authentication: OAuth for Upstox; app-level auth (JWT/session) for web and mobile.
- **FR-U3** Mandatory consent before enabling semi-auto or full-auto; consent event stored with timestamp and user id.

### 3.2 Market & Signals

- **FR-M1** Live index data (NIFTY, SENSEX) and 15-min/5-min/2-min candles via Upstox market data API.
- **FR-M2** Market bias: BUY only when 15-min EMA20 > EMA200; SELL only when 15-min EMA20 < EMA200; otherwise NO TRADE.
- **FR-M3** Time filter: trades allowed only in 09:20–10:30 and 11:15–12:30; entry cutoff 12:30.
- **FR-M4** CPR filter: if price inside CPR band → no trade (chop avoidance).
- **FR-M5** Pattern: only Bullish Engulfing (BUY) or Bearish Engulfing (SELL); no other candlestick patterns.
- **FR-M6** Entry sequence: 15-min trend → 5-min strong engulfing → 2-min pullback (1 candle) → next 2-min close above/below pullback high/low, and 2-min close above/below EMA20.
- **FR-M7** Option selection: NIFTY premium 180–220, SENSEX 480–520; ATM only; spread ≤ 5%; volume spike on entry candle.

### 3.3 Risk & Limits

- **FR-R1** Max 3 trades per day.
- **FR-R2** First loss of the day → stop all trading for the day.
- **FR-R3** Position sizing: 1 lot per trade; no scaling, no doubling.
- **FR-R4** Auto square-off: 15:15.

### 3.4 Execution & Modes

- **FR-E1** Manual: signals only; no auto orders.
- **FR-E2** Semi-auto: auto entry + SL; user manually manages exit (partial/trail).
- **FR-E3** Full-auto: automated entry, SL, partial at +0.6R, breakeven move, trail on 2-min EMA20.
- **FR-E4** Exit rules: 50% at +0.6R, SL to breakeven, trail remainder on 2-min EMA20.

### 3.5 Dashboard & Reporting

- **FR-D1** Market context: live index price, EMA20, EMA200, CPR levels, market bias.
- **FR-D2** Signal panel: signal status, reason, time-window validation, risk checklist (pass/fail).
- **FR-D3** Open positions: symbol, option type, entry price, live P&L, SL and trail state.
- **FR-D4** History: signal history, trade outcomes, rule violations.

### 3.6 Audit & Compliance

- **FR-A1** Full audit log: every signal, order, mode change, and risk decision with timestamp and actor.
- **FR-A2** No hardcoded credentials; secrets in vault/env; zero-trust assumptions.

---

## 4. Non-Functional Requirements

| NFR | Requirement |
|-----|-------------|
| **NFR-P** | Signal latency < 5 s from candle close under normal load. |
| **NFR-A** | 99.5% uptime for signal and order APIs during market hours (09:15–15:30 IST). |
| **NFR-S** | All secrets encrypted at rest and in transit; RBAC enforced on every API. |
| **NFR-O** | Structured logs and metrics for signals, orders, and errors; alerting on repeated failures. |
| **NFR-T** | Deterministic strategy logic; unit tests for all rule combinations; no flaky time-dependent tests in core logic. |

---

## 5. MVP vs Phase-2 Roadmap

### MVP (Phase 1)

- Upstox OAuth and market data (NIFTY, SENSEX; 15/5/2 min).
- Trend-Continuation Capital Preserver: bias, time, CPR, engulfing only, entry sequence, option filters.
- Risk engine: max 3 trades/day, 1-loss stop, 1 lot, square-off 15:15.
- Manual + Semi-auto modes (signals; semi-auto: auto entry + SL).
- Web dashboard: market context, signal panel, open positions, history.
- PostgreSQL (trades, signals, audits), Redis (state, locks).
- Event-driven backend (market → signal → risk → order).
- Audit log and RBAC (Trader/Admin).

### Phase 2

- Full-auto mode with partial exit, breakeven, and 2-min EMA20 trail.
- Mobile app (React Native) with same logic and views as web.
- Advanced observability (dashboards, SLOs, runbooks).
- Optional: BANKNIFTY support with separate premium/CPR rules.

---

## 6. Assumptions

- Upstox API availability and rate limits are sufficient for 15/5/2 min data and order execution.
- Users have sufficient margin and understand options risk; product does not replace legal/risk disclaimers.
- NSE market hours and index/options symbols remain consistent with current documentation.
- Single deployment region (e.g. India) is acceptable for latency.
- Strategy owner accepts that “no trade” is a valid and frequent outcome.

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Broker API downtime or changes | Circuit breaker, retries, and fallback to “no trade”; monitor API health. |
| Incorrect EMA/CPR or data lag | Validate data pipeline; reconcile with broker where possible; alert on anomalies. |
| Unintended auto execution | Mandatory consent, mode in Redis/DB, and kill switch (disable auto). |
| Credential leak | No hardcoded secrets; rotation policy; least-privilege access. |

---

## 8. Kill Criteria

- Repeated unexplained losses attributed to system logic or execution (e.g. wrong side, wrong quantity).
- Persistent failure to meet NFR-P or NFR-A after remediation.
- Regulatory or broker requirement that cannot be met without fundamental redesign.
- Decision by product/risk to discontinue the product; all user data and audit logs retained per policy.

---

## 9. Out of Scope (Explicit)

- Non-Upstox brokers.
- Non-index options (e.g. equity options, futures only).
- Doji, Hammer, Shooting Star, or any pattern other than Bullish/Bearish Engulfing.
- Counter-trend trading.
- Multiple lots, scaling, or martingale-style sizing.
- Marketing or promotional content in the core product docs.

---

*Document owner: Principal Product Manager (FinTech). Review cycle: per release.*
