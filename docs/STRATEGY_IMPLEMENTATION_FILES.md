# Strategy implementation – files and organization

This document lists all **required and supporting files** for the final strategy (buy, stop-loss, book profit).

---

## 1. Strategy logic (core)

| File | Role |
|------|------|
| `backend/app/services/strategy_engine.py` | Option B evaluation: time window 9:20–14:45, no trade inside CPR, six triggers (CPR bottom/top, support bounce, resistance rejection, engulfing+2m). Produces BUY/SELL/NO_SIGNAL. |
| `backend/app/services/pattern_detector.py` | Pattern detection: support bounce, resistance rejection, CPR bottom bounce, CPR top rejection, bullish/bearish engulfing. All on 5m (or 5m+2m for engulfing). |
| `backend/app/api/signals.py` | Fetches candles/indicators, builds context, calls strategy, applies risk checks. Returns signal + **suggested_sl_price** and **suggested_target_price** (from signal candle). |

---

## 2. Orders, SL, and positions

| File | Role |
|------|------|
| `backend/app/api/orders.py` | Place order (accepts `sl_trigger`, `target_premium`), list positions, trail SL `POST /positions/{id}/trail-sl`, order/history. On each new order it logs an **OPEN** trade event for end-of-day reporting. |
| `backend/app/services/position_store.py` | In-memory store for positions (entry, sl_trigger, order_id, etc.). When a position is closed it logs a **CLOSE** trade event for reporting. |
| `backend/app/services/order_manager.py` | Placeholder for actual broker order placement (Upstox). |
| `backend/app/services/trade_logger.py` | Trade logger: appends OPEN/CLOSE rows to `backend/app/logs/trades/trades-YYYY-MM-DD.csv` and can send a daily summary email using `send_daily_trade_report_email()`. |

---

## 3. Market data and indicators

| File | Role |
|------|------|
| `backend/app/services/upstox_service.py` | Upstox API: candles, instruments, auth. |
| `backend/app/services/candle_utils.py` | EMA/CPR and candle helpers used by strategy and signals. |

---

## 4. Documentation

| File | Role |
|------|------|
| `docs/FINAL_STRATEGY_HIGH_PROBABILITY.md` | Full strategy: filters, 3 BUY + 3 SELL triggers, flow, **entry/SL/book profit** section, implementation checklist. |
| `docs/STRATEGY_IMPLEMENTATION_FILES.md` | This file – index of strategy and supporting files. |
| `docs/STRATEGY_AND_DATA.md` | Strategy rules and data sources (aligned with final strategy). |
| `docs/BRD.md` | Business requirements (FR-M2–FR-M6) for time, CPR, patterns. |
| `docs/ARCHITECTURE.md` | High-level architecture; time filter 09:20–14:45. |

---

## 5. Frontend (signals and trade settings)

| File | Role |
|------|------|
| `web/src/app/page.tsx` | Dashboard: Evaluate (calls signal API), trade settings (target premium, etc.), positions table (shows sl_trigger), retry when backend unreachable. |

---

## 6. Run and deployment

| File | Role |
|------|------|
| `HOW-TO-RUN.md` | 5-step run, .env, Run from VS Code. |
| `BACKEND-NOT-REACHABLE-FIX.md` | Fix “Backend unreachable”. |
| `HOST-IN-CLOUD.md` | Vercel + Render deployment. |
| `backend/requirements.txt` | Python deps for Render/backend. |

---

## Quick check: buy, stop-loss, book profit

- **Buy/Sell signals:** Implemented in `strategy_engine.py` + `pattern_detector.py`; exposed by `signals.py` (GET `/signals/evaluate/{symbol}`).
- **Stop-loss:** Sent with order as `sl_trigger`; stored on position; signal API returns `suggested_sl_price` (index level) to pre-fill.
- **Book profit:** Order request has `target_premium`; signal API returns `suggested_target_price` (2R index level) to pre-fill.

Daily CSV logs of trades (1 row per OPEN/CLOSE event) are written by `trade_logger.py`, and you can trigger an end-of-day email report with `send_daily_trade_report_email()`.

All required and supporting files for this strategy are listed above and organized by role.
