# Strategy Implemented & Data

## 1. Final Strategy: High-Probability Signals (Option B)

**Full spec:** [FINAL_STRATEGY_HIGH_PROBABILITY.md](FINAL_STRATEGY_HIGH_PROBABILITY.md).

### Rules (in code)

| Step | Rule | Where in code |
|------|------|----------------|
| 1. **Time filter** | **09:20–14:45 IST** (9:20 AM to 2:45 PM) | `strategy_engine.is_in_trading_window()` |
| 2. **CPR band** | Price **inside** CPR → no trade. **CPR bottom bounce** → BUY; **CPR top rejection** → SELL | `strategy_engine.is_price_in_cpr()`; `pattern_detector.detect_cpr_bottom_bounce`, `detect_cpr_top_rejection` |
| 3. **No 15m bias** | Signals do not require 15m EMA20 vs EMA200 (Option B) | `strategy_engine.evaluate()` |
| 4. **BUY** | Support bounce (5m), CPR bottom bounce (5m), or Bullish engulfing + 2m entry | `pattern_detector` + `strategy_engine.evaluate()` |
| 5. **SELL** | Resistance rejection (5m), CPR top rejection (5m), or Bearish engulfing + 2m entry | `pattern_detector` + `strategy_engine.evaluate()` |
| 6. **Entry sequence** | For **engulfing** path only: 2m pullback → next 2m close above/below pullback and 2m EMA20 | `strategy_engine.check_entry_sequence()` |

The main entry is **`strategy_engine.evaluate(ctx, engulfing, ..., cpr_bottom_bounce, cpr_top_rejection)`**. The signals API builds context from 15m/5m/2m candles and runs the strategy on each evaluate.

---

## 2. Signals Pipeline (Implemented)

The end-to-end pipeline is **implemented**:

- **Dashboard** calls `/api/v1/signals/evaluate/NIFTY` when Upstox is connected (and refreshes every 30s).
- **Signals API** (`backend/app/api/signals.py`):
  - Gets the stored Upstox token.
  - Fetches **15m, 5m, 2m candles** from Upstox v3 historical API (`candle_service`).
  - Computes **EMA20, EMA200** (15m), **EMA20** (5m, 2m), and **CPR** from the latest 15m candle.
  - Builds **MarketContext**, detects **engulfing** on last two 5m candles, checks **entry sequence** on last two 2m candles.
  - Runs **risk_engine** (daily limits) and **strategy_engine.evaluate(...)**.
  - Returns **status** (BUY / SELL / NO_SIGNAL), **reason**, and **risk_checklist**.
- **Candle data** is **not persisted**; it is fetched on each evaluate request. For production, add Redis/DB and optional caching.

---

## 3. Where Fetched Data Is Stored

### Currently implemented

| Data | Source | Stored? | Where used |
|------|--------|--------|------------|
| **NIFTY / SENSEX last price (LTP)** | Upstox `market-quote/quotes` | **No** | Fetched on each request in `/api/v1/market/context/{symbol}`, returned to frontend; not written to DB or Redis. |
| **Upstox access token** | OAuth or pasted token | **Yes (in memory)** | In `auth._upstox_token_store`; used for all Upstox API calls. Not in DB/Redis yet. |

So the only “fetched” data we have is **live index LTP**; it is **not** stored—it’s fetched on demand and sent to the dashboard.

### Not implemented yet (needed for signals)

| Data | Intended storage | Purpose |
|------|------------------|--------|
| **15-min / 5-min / 2-min candles** | PostgreSQL (and/or Redis for latest) | Compute EMAs, CPR, engulfing, entry sequence. |
| **EMA20, EMA200, CPR** | Redis (latest) or derived on demand | Input to `strategy_engine.evaluate()`. |
| **Signals** | PostgreSQL | Persist each signal (time, symbol, BUY/SELL, reason, risk checklist) and serve to dashboard / history. |
| **Trades / positions** | PostgreSQL | P&L, trades today, win rate, open positions. |

---

## 4. What Needs to Be Built for Signals to Show

1. **Candle fetcher**  
   Use Upstox historical/feed API to get 15m, 5m, and 2m candles for NIFTY (and SENSEX if needed). Run on a schedule or on 2m candle close.

2. **Storage**  
   Save candles (and optionally latest EMAs/CPR) in **PostgreSQL** and/or **Redis**.

3. **EMA & CPR**  
   Compute 15m EMA20 & EMA200, 5m/2m EMA20, and CPR from stored candles.

4. **Wire strategy to API**  
   In `signals.evaluate_signal(symbol)`:
   - Load or compute **MarketContext** (EMAs, CPR, last candles) for that symbol.
   - Run **pattern_detector** on 5m candles and **strategy_engine.evaluate(ctx, engulfing)**.
   - Run **risk_engine** (daily limits, time window, etc.).
   - Persist the signal and return it from the API.

5. **Dashboard**  
   Call `/api/v1/signals/evaluate/NIFTY` (and SENSEX) when connected; display returned status, reason, and risk checklist in the Signal panel and (optionally) in Summary.

Once this pipeline is in place, the **same strategy** we already implemented in code will produce real **BUY/SELL/NO_SIGNAL** and the dashboard will show them.
