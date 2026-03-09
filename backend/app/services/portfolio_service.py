import asyncio
import logging
import httpx

_log = logging.getLogger(__name__)

# In-memory: instrument_key -> quantity_sold (for reduce-then-buy-back strategy).
# Cleared when user records buy-back. Use DB in production.
_reduced_holdings: dict[str, int] = {}


def record_reduced(instrument_key: str, quantity_sold: int) -> None:
    """Record that user reduced holding by quantity_sold (for buy-back suggestion)."""
    key = (instrument_key or "").strip()
    if key:
        _reduced_holdings[key] = max(0, quantity_sold)


def clear_buyback_done(instrument_key: str) -> None:
    """Clear reduced state after user buys back."""
    key = (instrument_key or "").strip()
    if key and key in _reduced_holdings:
        del _reduced_holdings[key]


def get_reduced_qty(instrument_key: str) -> int:
    """Return quantity currently in 'reduced' state for this instrument (0 if none)."""
    return _reduced_holdings.get((instrument_key or "").strip(), 0)


async def fetch_upstox_holdings_meta(token: str) -> dict:
    """
    Fetch long-term holdings from Upstox (stocks in demat).
    Upstox v2 endpoint: GET /v2/portfolio/long-term-holdings
    Returns dict: { ok, status_code, items, error }.
    """
    url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )
        if resp.status_code != 200:
            _log.warning("Upstox holdings: HTTP %s: %s", resp.status_code, resp.text[:2000])
            return {"ok": False, "status_code": resp.status_code, "items": [], "error": resp.text[:500]}
        body = resp.json() or {}
        data = body.get("data") or []
        items = data if isinstance(data, list) else []
        return {"ok": True, "status_code": resp.status_code, "items": items, "error": None}
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox holdings request error: %s", e)
        return {"ok": False, "status_code": None, "items": [], "error": str(e)}
    except Exception as e:
        _log.warning("Upstox holdings unexpected error: %s", e, exc_info=True)
        return {"ok": False, "status_code": None, "items": [], "error": str(e)}


async def fetch_upstox_holdings(token: str) -> list[dict]:
    meta = await fetch_upstox_holdings_meta(token)
    return meta.get("items") or []


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


async def analyze_intraday_opportunity_15m(
    token: str,
    instrument_key: str,
) -> dict:
    """
    Lightweight intraday opportunity on 15m for a holding.
    Logic:
    - compute 15m EMA20 vs EMA200 bias from recent candles
    - detect Bullish/Bearish Engulfing on last 2 candles
    - opportunity only when pattern aligns with bias
    """
    from datetime import timedelta

    from app.services.candle_service import (
        _candle_sort_key,
        _candle_dt_ist,
        _ema,
        _now_ist,
        fetch_candles_instrument,
        fetch_intraday_candles_instrument,
    )
    from app.services.pattern_detector import detect_engulfing

    instrument_key = (instrument_key or "").strip()
    if not instrument_key:
        return {"status": "NO_SIGNAL", "reason": "Missing instrument_key"}

    today = _now_ist().date()
    from_date = today - timedelta(days=12)

    hist, intra = await asyncio.gather(
        fetch_candles_instrument(token, instrument_key, 15, today, from_date),
        fetch_intraday_candles_instrument(token, instrument_key, 15),
    )

    merged: dict[str, dict] = {}
    for c in (hist or []) + (intra or []):
        ts = str(c.get("timestamp") or "").strip()
        if ts:
            merged[ts] = c
    candles = sorted(merged.values(), key=_candle_sort_key)

    if len(candles) < 3:
        return {"status": "NO_SIGNAL", "reason": "Not enough 15m candles"}

    closes = [float(c["close"]) for c in candles if "close" in c]
    ema20 = _ema(closes, 20) if closes else 0.0
    ema200 = _ema(closes, 200) if closes else 0.0
    bias = "BUY" if ema20 > ema200 else ("SELL" if ema20 < ema200 else "NO_TRADE")

    prev, curr = candles[-2], candles[-1]
    prev_dt = _candle_dt_ist(prev)
    curr_dt = _candle_dt_ist(curr)
    last_time = curr_dt.strftime("%Y-%m-%dT%H:%M") if curr_dt else None

    # Avoid cross-day engulfing (yesterday's last candle vs today's first candle).
    if prev_dt and curr_dt and prev_dt.date() != curr_dt.date():
        return {
            "status": "NO_SIGNAL",
            "reason": "Waiting for today's 15m candles (latest candle is from previous day)",
            "bias": bias,
            "ema20": round(ema20, 2) if ema20 else None,
            "ema200": round(ema200, 2) if ema200 else None,
            "last_15m_time": last_time,
        }

    patt = detect_engulfing(prev, curr, min_body_ratio=1.2)

    if not patt:
        return {
            "status": "NO_SIGNAL",
            "reason": f"No engulfing on 15m (bias {bias})",
            "bias": bias,
            "ema20": round(ema20, 2) if ema20 else None,
            "ema200": round(ema200, 2) if ema200 else None,
            "last_15m_time": last_time,
        }

    if bias != patt.direction:
        return {
            "status": "NO_SIGNAL",
            "reason": f"Engulfing {patt.direction} but bias {bias}",
            "bias": bias,
            "pattern": f"{patt.direction}_ENGULFING",
            "pattern_strength": round(patt.body_ratio, 2),
            "ema20": round(ema20, 2) if ema20 else None,
            "ema200": round(ema200, 2) if ema200 else None,
            "last_15m_time": last_time,
        }

    return {
        "status": "SIGNAL",
        "direction": patt.direction,
        "reason": f"15m engulfing aligns with EMA trend ({bias})",
        "bias": bias,
        "pattern": f"{patt.direction}_ENGULFING",
        "pattern_strength": round(patt.body_ratio, 2),
        "ema20": round(ema20, 2) if ema20 else None,
        "ema200": round(ema200, 2) if ema200 else None,
        "last_15m_time": last_time,
    }


async def analyze_holdings_reduce_buyback(
    token: str,
    instrument_key: str,
    quantity: int,
    reduce_pct: int,
) -> dict:
    """
    Reduce-on-weakness / Buy-back-on-strength strategy for holdings (15m).
    - REDUCE: price going down + bearish 15m (below EMA20, bearish engulfing) -> sell reduce_pct% of holding.
    - BUY_BACK: after reduce, when 15m shows bullish (bullish engulfing, price above EMA20) -> buy back the sold qty.
    reduce_pct: 20, 30, or 50 (percent of holding to reduce).
    Returns: action (REDUCE | BUY_BACK | NO_ACTION), suggested_qty, reason, last_15m_time, etc.
    """
    from datetime import timedelta

    from app.services.candle_service import (
        _candle_sort_key,
        _candle_dt_ist,
        _ema,
        _now_ist,
        fetch_candles_instrument,
        fetch_intraday_candles_instrument,
    )
    from app.services.pattern_detector import detect_engulfing

    instrument_key = (instrument_key or "").strip()
    if not instrument_key:
        return {"action": "NO_ACTION", "reason": "Missing instrument_key", "suggested_qty": 0, "reduce_pct": reduce_pct}

    qty = max(0, int(quantity))
    pct = max(10, min(80, int(reduce_pct)))  # clamp 10–80

    today = _now_ist().date()
    from_date = today - timedelta(days=12)

    hist, intra = await asyncio.gather(
        fetch_candles_instrument(token, instrument_key, 15, today, from_date),
        fetch_intraday_candles_instrument(token, instrument_key, 15),
    )
    merged: dict[str, dict] = {}
    for c in (hist or []) + (intra or []):
        ts = str(c.get("timestamp") or "").strip()
        if ts:
            merged[ts] = c
    candles = sorted(merged.values(), key=_candle_sort_key)

    if len(candles) < 3:
        return {
            "action": "NO_ACTION",
            "reason": "Not enough 15m candles",
            "suggested_qty": 0,
            "reduce_pct": pct,
            "last_15m_time": None,
        }

    closes = [float(c["close"]) for c in candles if "close" in c]
    ema20 = _ema(closes, 20) if closes else 0.0
    ema200 = _ema(closes, 200) if closes else 0.0
    last_close = float(candles[-1]["close"]) if candles else 0.0

    prev, curr = candles[-2], candles[-1]
    prev_dt = _candle_dt_ist(prev)
    curr_dt = _candle_dt_ist(curr)
    last_time = curr_dt.strftime("%Y-%m-%dT%H:%M") if curr_dt else None

    if prev_dt and curr_dt and prev_dt.date() != curr_dt.date():
        return {
            "action": "NO_ACTION",
            "reason": "Waiting for today's 15m candles",
            "suggested_qty": 0,
            "reduce_pct": pct,
            "last_15m_time": last_time,
        }

    patt = detect_engulfing(prev, curr, min_body_ratio=1.2)
    reduced_qty = get_reduced_qty(instrument_key)

    # BUY_BACK: we have reduced state and 15m shows bullish (engulfing + price above EMA20)
    if reduced_qty > 0 and patt and patt.direction == "BUY" and ema20 and last_close >= ema20 * 0.998:
        return {
            "action": "BUY_BACK",
            "reason": "15m bullish engulfing, price above EMA20 – buy back reduced portion",
            "suggested_qty": reduced_qty,
            "reduce_pct": pct,
            "last_15m_time": last_time,
            "ema20": round(ema20, 2),
            "ema200": round(ema200, 2) if ema200 else None,
        }

    # REDUCE: price going down (below EMA20) and bearish engulfing
    if patt and patt.direction == "SELL" and ema20 and last_close <= ema20 * 1.002:
        suggest = max(1, (qty * pct) // 100)
        return {
            "action": "REDUCE",
            "reason": "15m bearish engulfing, price below EMA20 – reduce holding",
            "suggested_qty": min(suggest, qty),
            "reduce_pct": pct,
            "last_15m_time": last_time,
            "ema20": round(ema20, 2),
            "ema200": round(ema200, 2) if ema200 else None,
        }

    if reduced_qty > 0:
        return {
            "action": "NO_ACTION",
            "reason": f"Reduced qty {reduced_qty} – wait for bullish 15m to buy back",
            "suggested_qty": reduced_qty,
            "reduce_pct": pct,
            "last_15m_time": last_time,
        }

    return {
        "action": "NO_ACTION",
        "reason": "No reduce/buy-back signal on 15m",
        "suggested_qty": 0,
        "reduce_pct": pct,
        "last_15m_time": last_time,
    }

