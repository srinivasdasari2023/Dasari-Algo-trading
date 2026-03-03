# Strategy Implemented & Why Signals Don’t Show Yet

## 1. Strategy We Implemented: Trend-Continuation Capital Preserver

The **logic** is in the backend; it is **not yet wired** to live data or the API.

### Rules (in code)

| Step | Rule | Where in code |
|------|------|----------------|
| 1. **Market bias** | 15-min EMA20 > EMA200 → **BUY only**; EMA20 < EMA200 → **SELL only**; else **NO TRADE** | `strategy_engine.get_bias()` |
| 2. **Time filter** | Allowed: 09:20–10:30 and 11:15–12:30 IST; entry cutoff 12:30 | `strategy_engine.is_in_trading_window()` (TODO: IST check) |
| 3. **CPR filter** | If price is inside CPR band → **no trade** (chop avoidance) | `strategy_engine.is_price_in_cpr()` |
| 4. **Pattern** | **Only** Bullish Engulfing (BUY) or Bearish Engulfing (SELL) on 5-min | `pattern_detector.detect_engulfing()` |
| 5. **Entry sequence** | 2-min pullback (1 candle) → next 2-min close above/below pullback high/low; 2-min close above/below EMA20 | `strategy_engine.check_entry_sequence()` |
| 6. **Option filter** | NIFTY premium 180–220, SENSEX 480–520; ATM; spread ≤ 5%; volume spike | Not implemented yet |

**Candlestick & price action:** Entry signals use **candlestick patterns** (bullish/bearish engulfing on 5m) and **price action** (EMAs, CPR, 2m entry sequence). **Stop loss** is set at order place (`sl_trigger`); trailing SL is updated via API. Strategy-derived SL from price action (e.g. swing low/high, ATR) can be added later.

The main entry is **`strategy_engine.evaluate(ctx, engulfing)`**: it needs a **MarketContext** (EMAs, CPR, OHLC) and an optional **EngulfingResult**. The signals pipeline builds this from live 15m/5m/2m candles and runs the strategy on each evaluate.

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
