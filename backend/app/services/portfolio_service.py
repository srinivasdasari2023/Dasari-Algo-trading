import asyncio
import logging
import httpx

_log = logging.getLogger(__name__)


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
    patt = detect_engulfing(prev, curr, min_body_ratio=1.2)
    last_dt = _candle_dt_ist(curr)
    last_time = last_dt.strftime("%Y-%m-%dT%H:%M") if last_dt else None

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

