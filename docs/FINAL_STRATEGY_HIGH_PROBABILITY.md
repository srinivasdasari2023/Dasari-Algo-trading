# Final Strategy – High-Probability Profit Signals

Single strategy that combines **support/resistance patterns**, **engulfing + 2m entry**, and **CPR signal points**, with **no 15m EMA bias dependency** (Option B), to aim for higher-probability signals.

---

## 1. Filters (apply to every signal)

| Filter | Rule | Purpose |
|--------|------|--------|
| **Time window** | Trade only **09:20–14:45** IST (9:20 AM to 2:45 PM) | Single window from open to 15 minutes before market close. |
| **CPR band (inside)** | If price is **inside** CPR (low to high of candle overlaps band), **no trade** | Avoid chop in the middle of the range. |
| **Risk** | Daily loss stop; max 3 trades/day (configurable) | Capital preservation. |

**No 15m EMA20 vs EMA200 check** – we do not require “bias” to allow a signal (Option B).

---

## 2. BUY signals (any one of the following)

### 2.1 Support bounce (5m)

- **Last 5m candle:** Low touches support (prior low or EMA20, or last 3 candles’ low).
- **Close:** Green (close > open) and close **above EMA20 (5m)** (or within small tolerance).
- **Context:** Price tested support and bounced; we take the bounce.

### 2.2 CPR bottom bounce (5m)

- **Last 5m candle:** Low touches or goes **below CPR bottom** (within tolerance).
- **Close:** Green and close **above CPR bottom** (or above EMA20).
- **Context:** CPR bottom acts as support; bounce = BUY.

### 2.3 Bullish engulfing + 2m entry (5m + 2m)

- **Last two 5m candles:** Bullish engulfing (current green candle engulfs previous red; body ratio ≥ 1.2).
- **Last two 2m candles:** Pullback then next 2m close above pullback high and above 2m EMA20.
- **Context:** Trend-style continuation with confirmation.

---

## 3. SELL signals (any one of the following)

### 3.1 Resistance rejection (5m)

- **Last 5m candle:** High touches resistance (prior high or EMA20, or last 3 candles’ high).
- **Close:** Red (close < open) and close **at or below EMA20 (5m)** (or within small tolerance).
- **Context:** Price tested resistance and rejected; we take the rejection.

### 3.2 CPR top rejection (5m)

- **Last 5m candle:** High touches or goes **above CPR top** (within tolerance).
- **Close:** Red and close **below CPR top** (or below EMA20).
- **Context:** CPR top acts as resistance; rejection = SELL.

### 3.3 Bearish engulfing + 2m entry (5m + 2m)

- **Last two 5m candles:** Bearish engulfing (current red candle engulfs previous green; body ratio ≥ 1.2).
- **Last two 2m candles:** Pullback then next 2m close below pullback low and below 2m EMA20.
- **Context:** Trend-style continuation with confirmation.

---

## 4. Summary table

| Signal | Trigger condition | Timeframe |
|--------|-------------------|-----------|
| **BUY** | Support bounce (low at support, close green above EMA20) | 5m |
| **BUY** | CPR bottom bounce (low at CPR bottom, close green above CPR bottom/EMA20) | 5m |
| **BUY** | Bullish engulfing + 2m entry confirmation | 5m + 2m |
| **SELL** | Resistance rejection (high at resistance, close red at/below EMA20) | 5m |
| **SELL** | CPR top rejection (high at CPR top, close red below CPR top/EMA20) | 5m |
| **SELL** | Bearish engulfing + 2m entry confirmation | 5m + 2m |

**Filters for all:** Time window (**9:20 AM–2:45 PM** IST); no trade when price is **inside** CPR band; risk (daily loss stop, max trades).

---

## 5. Flow (simplified)

1. **Time in window?** (9:20–14:45 IST) No → NO_SIGNAL.  
2. **Price inside CPR band?** Yes → NO_SIGNAL (chop filter).  
3. **Risk (daily stop / max trades)?** Not allowed → NO_SIGNAL.  
4. **Check patterns (order doesn’t matter):**
   - CPR bottom bounce → **BUY**
   - CPR top rejection → **SELL**
   - Support bounce → **BUY**
   - Resistance rejection → **SELL**
   - Bullish engulfing + 2m entry → **BUY**
   - Bearish engulfing + 2m entry → **SELL**
5. If none of the above → NO_SIGNAL.

---

## 6. Why this aims for high probability

- **Multiple confluences:** S/R levels, CPR levels, and engulfing + 2m all require clear price action (bounce/rejection or engulfing + confirmation).
- **Chop filter:** No trade inside CPR band reduces low-edge trades in the middle of the range.
- **Time filter:** Restricts to higher-liquidity windows.
- **No EMA bias:** Allows valid bounces and rejections even when 15m trend hasn’t “confirmed” yet (Option B), so you don’t miss clear S/R and CPR signals.
- **CPR as signal points:** Uses a strong level (CPR) for extra high-probability entries at support (BUY) and resistance (SELL).

---

## 7. Entry, stop-loss, and book profit (in code)

| Item | In code | Notes |
|------|--------|--------|
| **Entry** | Yes | BUY/SELL from the six triggers above; time 9:20–14:45 IST, no trade inside CPR. |
| **Stop-loss (SL)** | Yes | Order API accepts `sl_trigger`; positions store SL; you can send **suggested_sl_price** from the signal (index level) or set your own. API also supports trailing SL via `POST /positions/{id}/trail-sl`. |
| **Book profit / target** | Yes | Order request has `target_premium` (e.g. NIFTY ~200, SENSEX ~500). Signal response includes **suggested_target_price** (index level, 2R from signal candle); you can use it or your own target premium. |

**Suggested levels from strategy:** When the API returns BUY or SELL, it also returns:
- **suggested_sl_price** – index level: for BUY = signal candle low − buffer (5 NIFTY / 10 SENSEX); for SELL = signal candle high + buffer.
- **suggested_target_price** – index level: 2× risk (2R) from signal candle (BUY: close + 2R, SELL: close − 2R).

Use these to pre-fill SL and target in the dashboard or when placing orders. Actual order placement and broker SL/target are in `backend/app/api/orders.py` and trade settings (target premium).

---

## 8. Implementation checklist

- [x] Remove 15m bias requirement for all signals (Option B).
- [x] Add **CPR bottom bounce** → BUY (5m: low ≤ CPR bottom, close green above CPR bottom / EMA20).
- [x] Add **CPR top rejection** → SELL (5m: high ≥ CPR top, close red below CPR top / EMA20).
- [x] Keep: support bounce, resistance rejection, engulfing + 2m entry.
- [x] Keep: time window 9:20–14:45 IST, “no trade inside CPR”, risk rules.
- [ ] Optional: show “why NO_SIGNAL” on dashboard (which filter or “no pattern”).

**Related files:** See `docs/STRATEGY_IMPLEMENTATION_FILES.md` for the full list of strategy code and supporting files.
