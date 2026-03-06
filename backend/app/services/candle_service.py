"""
Fetch 15m, 5m, 2m candles from Upstox; compute EMA20, EMA200, CPR.
In-memory cache; use Redis/DB in production.
"""
import asyncio
import logging
from datetime import date, datetime as dt_parse, timedelta, timezone, time as dt_time
import urllib.parse
import httpx

_log = logging.getLogger(__name__)

# IST = UTC+5:30 (no zoneinfo/tzdata dependency on Windows)
IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc


def _now_ist() -> dt_parse:
    """Current time in IST. Use UTC now then convert so server TZ does not affect date."""
    return dt_parse.now(UTC).astimezone(IST)

# Upstox instrument keys
INDEX_KEYS: dict[str, str] = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "SENSEX": "BSE_INDEX|SENSEX",
}

# Cache: symbol -> interval -> list of candle dicts (newest last)
_candle_cache: dict[str, dict[str, list[dict]]] = {}
_cache_ts: dict[str, float] = {}  # symbol -> last fetch time
CACHE_TTL_SEC = 60  # refetch after 1 min


def _parse_candle(row: list) -> dict:
    """Parse Upstox candle row: [ts, o, h, l, c, vol, oi]."""
    return {
        "timestamp": row[0] if isinstance(row[0], str) else str(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": int(row[5]) if len(row) > 5 else 0,
    }


def _ema(series: list[float], period: int) -> float:
    """Exponential moving average. series = oldest first."""
    if not series or period <= 0:
        return 0.0
    if len(series) < period:
        return sum(series) / len(series)
    k = 2 / (period + 1)
    ema = sum(series[:period]) / period
    for i in range(period, len(series)):
        ema = series[i] * k + ema * (1 - k)
    return ema


def _cpr_from_candle(c: dict) -> tuple[float, float, float]:
    """CPR from one candle: pivot = (H+L+C)/3, BC = (H+L)/2, TC = 2*P - BC. Returns (pivot, bottom, top)."""
    h, l, close = c["high"], c["low"], c["close"]
    pivot = (h + l + close) / 3
    bc = (h + l) / 2
    tc = 2 * pivot - bc
    bottom = min(bc, tc)
    top = max(bc, tc)
    return pivot, bottom, top


async def fetch_candles(
    token: str,
    symbol: str,
    interval_min: int,
    to_date: date,
    from_date: date | None = None,
) -> list[dict]:
    """Fetch historical candles from Upstox v3. interval_min: 1, 2, 5, 15. Never raises; returns [] on error."""
    if symbol.upper() not in INDEX_KEYS:
        return []
    instrument_key = INDEX_KEYS[symbol.upper()]
    encoded = urllib.parse.quote(instrument_key, safe="")
    to_s = to_date.isoformat()
    from_s = (from_date or to_date).isoformat()
    url = f"https://api.upstox.com/v3/historical-candle/{encoded}/minutes/{interval_min}/{to_s}/{from_s}"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            _log.warning("Upstox candles %sm %s: HTTP %s", interval_min, symbol, resp.status_code)
            return []
        data = resp.json()
        candles = data.get("data", {}).get("candles", [])
        out = []
        for r in candles:
            try:
                out.append(_parse_candle(r))
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        return out
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox candles %sm %s: %s", interval_min, symbol, e)
        return []
    except Exception as e:
        _log.warning("Upstox candles %sm %s: %s", interval_min, symbol, e, exc_info=True)
        return []


async def fetch_candles_instrument(
    token: str,
    instrument_key: str,
    interval_min: int,
    to_date: date,
    from_date: date | None = None,
) -> list[dict]:
    """Fetch historical candles for an Upstox instrument_key (no symbol mapping). Never raises; returns [] on error."""
    if not instrument_key:
        return []
    encoded = urllib.parse.quote(str(instrument_key), safe="")
    to_s = to_date.isoformat()
    from_s = (from_date or to_date).isoformat()
    url = f"https://api.upstox.com/v3/historical-candle/{encoded}/minutes/{interval_min}/{to_s}/{from_s}"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            _log.warning("Upstox candles %sm %s: HTTP %s", interval_min, instrument_key, resp.status_code)
            return []
        data = resp.json()
        candles = data.get("data", {}).get("candles", [])
        out = []
        for r in candles:
            try:
                out.append(_parse_candle(r))
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        return out
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox candles %sm %s: %s", interval_min, instrument_key, e)
        return []
    except Exception as e:
        _log.warning("Upstox candles %sm %s: %s", interval_min, instrument_key, e, exc_info=True)
        return []


async def fetch_intraday_candles(
    token: str,
    symbol: str,
    interval_min: int,
) -> list[dict]:
    """Fetch current-day intraday candles from Upstox v3. Never raises; returns [] on error."""
    if symbol.upper() not in INDEX_KEYS:
        return []
    instrument_key = INDEX_KEYS[symbol.upper()]
    encoded = urllib.parse.quote(instrument_key, safe="")
    # Upstox v3 intraday endpoint
    url = f"https://api.upstox.com/v3/historical-candle/intraday/{encoded}/minutes/{interval_min}"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            _log.warning("Upstox intraday candles %sm %s: HTTP %s", interval_min, symbol, resp.status_code)
            return []
        data = resp.json()
        candles = data.get("data", {}).get("candles", [])
        out = []
        for r in candles:
            try:
                out.append(_parse_candle(r))
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        return out
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox intraday candles %sm %s: %s", interval_min, symbol, e)
        return []
    except Exception as e:
        _log.warning("Upstox intraday candles %sm %s: %s", interval_min, symbol, e, exc_info=True)
        return []


async def fetch_intraday_candles_instrument(
    token: str,
    instrument_key: str,
    interval_min: int,
) -> list[dict]:
    """Fetch current-day intraday candles for an instrument_key. Never raises; returns [] on error."""
    if not instrument_key:
        return []
    encoded = urllib.parse.quote(str(instrument_key), safe="")
    url = f"https://api.upstox.com/v3/historical-candle/intraday/{encoded}/minutes/{interval_min}"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            _log.warning("Upstox intraday candles %sm %s: HTTP %s", interval_min, instrument_key, resp.status_code)
            return []
        data = resp.json()
        candles = data.get("data", {}).get("candles", [])
        out = []
        for r in candles:
            try:
                out.append(_parse_candle(r))
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        return out
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox intraday candles %sm %s: %s", interval_min, instrument_key, e)
        return []
    except Exception as e:
        _log.warning("Upstox intraday candles %sm %s: %s", interval_min, instrument_key, e, exc_info=True)
        return []

async def fetch_daily_candles(
    token: str,
    symbol: str,
    to_date: date,
    from_date: date | None = None,
) -> list[dict]:
    """Fetch daily (1D) candles from Upstox v3. Returns list of candle dicts; [] on error."""
    if symbol.upper() not in INDEX_KEYS:
        return []
    instrument_key = INDEX_KEYS[symbol.upper()]
    encoded = urllib.parse.quote(instrument_key, safe="")
    to_s = to_date.isoformat()
    from_s = (from_date or to_date).isoformat()
    url = f"https://api.upstox.com/v3/historical-candle/{encoded}/days/1/{to_s}/{from_s}"
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            _log.warning("Upstox daily candles %s: HTTP %s", symbol, resp.status_code)
            return []
        data = resp.json()
        candles = data.get("data", {}).get("candles", [])
        out = []
        for r in candles:
            try:
                out.append(_parse_candle(r))
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        return out
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as e:
        _log.warning("Upstox daily candles %s: %s", symbol, e)
        return []
    except Exception as e:
        _log.warning("Upstox daily candles %s: %s", symbol, e, exc_info=True)
        return []


async def get_candles_and_indicators(
    token: str,
    symbol: str,
) -> tuple[list[dict], list[dict], list[dict], float, float, float, float, float | None, float | None, float | None]:
    """
    Fetch 15m, 5m, 2m candles for symbol; compute EMA20/200 for 15m, EMA20 for 5m/2m, CPR from latest 15m.
    Uses IST for "today". Fetches all three in parallel to avoid long wait.
    Returns (candles_15m, candles_5m, candles_2m, ema20_15m, ema200_15m, ema20_5m, ema20_2m, cpr_pivot, cpr_bottom, cpr_top).
    """
    today_ist = _now_ist().date()
    from_15 = today_ist - timedelta(days=10)
    from_5 = today_ist - timedelta(days=7)  # 7 days so chart has previous days' 5m candles
    from_2 = today_ist - timedelta(days=1)

    hist_15m, hist_5m, hist_2m, intra_15m, intra_5m, intra_2m = await asyncio.gather(
        fetch_candles(token, symbol, 15, today_ist, from_15),
        fetch_candles(token, symbol, 5, today_ist, from_5),
        fetch_candles(token, symbol, 2, today_ist, from_2),
        fetch_intraday_candles(token, symbol, 15),
        fetch_intraday_candles(token, symbol, 5),
        fetch_intraday_candles(token, symbol, 2),
    )

    def _merge_sort(*lists: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        for lst in lists:
            for c in lst or []:
                ts = str(c.get("timestamp") or "").strip()
                if not ts:
                    continue
                merged[ts] = c
        # ISO timestamps sort correctly as strings (Upstox uses ISO with +05:30)
        return sorted(merged.values(), key=lambda c: str(c.get("timestamp") or ""))

    # Merge intraday into historical so "today" candles are present even when historical API lags
    candles_15m = _merge_sort(hist_15m, intra_15m)
    candles_5m = _merge_sort(hist_5m, intra_5m)
    candles_2m = _merge_sort(hist_2m, intra_2m)

    closes_15 = [c["close"] for c in candles_15m]
    closes_5 = [c["close"] for c in candles_5m]
    closes_2 = [c["close"] for c in candles_2m]

    ema20_15m = _ema(closes_15, 20) if len(closes_15) >= 20 else (closes_15[-1] if closes_15 else 0.0)
    ema200_15m = _ema(closes_15, 200) if len(closes_15) >= 200 else (closes_15[-1] if closes_15 else 0.0)
    ema20_5m = _ema(closes_5, 20) if len(closes_5) >= 20 else (closes_5[-1] if closes_5 else None)
    ema200_5m = _ema(closes_5, 200) if len(closes_5) >= 200 else (closes_5[-1] if closes_5 else None)
    ema20_2m = _ema(closes_2, 20) if len(closes_2) >= 20 else (closes_2[-1] if closes_2 else None)

    cpr_pivot = cpr_bottom = cpr_top = None
    if candles_15m:
        last_15 = candles_15m[-1]
        cpr_pivot, cpr_bottom, cpr_top = _cpr_from_candle(last_15)

    return (
        candles_15m,
        candles_5m,
        candles_2m,
        ema20_15m,
        ema200_15m,
        ema20_5m or 0.0,
        ema200_5m or 0.0,
        ema20_2m or 0.0,
        cpr_pivot,
        cpr_bottom,
        cpr_top,
    )


def _candle_dt_ist(c: dict):
    """Parse candle timestamp to datetime in IST. Returns None on failure."""
    try:
        raw = c.get("timestamp")
        if raw is None:
            return None
        ts = str(raw).strip()
        if not ts:
            return None
        if "T" in ts:
            dt = dt_parse.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo:
                return dt.astimezone(IST)
            # Naive timestamp: assume UTC (API standard), convert to IST so market hours show 9:15–15:30
            return dt.replace(tzinfo=UTC).astimezone(IST)
        if ts[:10].replace("-", "").isdigit() and len(ts) >= 10:
            return dt_parse.strptime(ts[:10], "%Y-%m-%d").replace(tzinfo=IST)
        try:
            epoch = float(ts)
            if epoch > 1e12:
                epoch = epoch / 1000.0
            return dt_parse.fromtimestamp(epoch, tz=IST)
        except (ValueError, OSError):
            pass
        return None
    except Exception:
        return None


def _candle_date_ist(c: dict) -> date | None:
    """Parse candle timestamp to date in IST. Handles ISO string or epoch (ms/s)."""
    dt = _candle_dt_ist(c)
    return dt.date() if dt else None


def _daily_candle_trading_date(c: dict) -> date | None:
    """For daily candles: return trading date from timestamp string (YYYY-MM-DD). Avoids UTC session-end shifting date in IST."""
    raw = c.get("timestamp")
    if raw is None:
        return None
    s = str(raw).strip()[:10]
    if len(s) == 10 and s[:4].isdigit() and s[4] == "-" and s[5:7].isdigit() and s[7] == "-" and s[8:10].isdigit():
        try:
            return dt_parse.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            pass
    return _candle_date_ist(c)


def _candle_sort_key(c: dict) -> float:
    """Epoch (seconds) for sorting candles chronologically."""
    dt = _candle_dt_ist(c)
    return dt.timestamp() if dt else 0.0


# NSE/BSE market hours IST: 9:15 AM – 3:30 PM. Opening range = first candle at 9:15.
MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)
OPENING_TIME = dt_time(9, 15)


def _is_market_hours_ist(dt: dt_parse) -> bool:
    """True if time is within NSE market hours 9:15–15:30 IST."""
    if not dt or dt.tzinfo is None:
        return False
    t = dt.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


def _opening_candle_today(candles_today: list[dict], today_ist: date):
    """Return the opening candle (9:15 AM IST) from today's list; else earliest candle of the day."""
    if not candles_today:
        return None
    sorted_c = sorted(candles_today, key=_candle_sort_key)
    for c in sorted_c:
        dt = _candle_dt_ist(c)
        if not dt or dt.date() != today_ist:
            continue
        t = dt.time()
        if t == OPENING_TIME:
            return c
        if t >= MARKET_OPEN:
            return c
    return sorted_c[0]


def _candles_in_window_ist(
    candles: list[dict],
    day_ist: date,
    start_t: dt_time,
    end_t: dt_time,
) -> list[dict]:
    """Candles whose IST timestamp is within [start_t, end_t)."""
    out: list[dict] = []
    for c in candles or []:
        dt = _candle_dt_ist(c)
        if not dt or dt.date() != day_ist:
            continue
        t = dt.time()
        if start_t <= t < end_t:
            out.append(c)
    return sorted(out, key=_candle_sort_key)


def _candles_at_times_ist(
    candles: list[dict],
    day_ist: date,
    times: set[dt_time],
) -> list[dict]:
    """Candles whose IST timestamp time() matches one of the provided times."""
    out: list[dict] = []
    for c in candles or []:
        dt = _candle_dt_ist(c)
        if not dt or dt.date() != day_ist:
            continue
        if dt.time() in times:
            out.append(c)
    return sorted(out, key=_candle_sort_key)


async def get_extended_market_context(token: str, symbol: str) -> dict:
    """
    Extended context: CPR (with width & trend hint), today 5m/15m range, prev day H/L, EMAs.
    Uses IST for market day. Candles sorted by time so opening range = first candle of day.
    Returns dict for dashboard.
    """
    # Use IST for "today" and "yesterday" so market session dates are correct regardless of server TZ
    now_ist = dt_parse.now(IST)
    today_ist = now_ist.date()
    yesterday_ist = today_ist - timedelta(days=1)

    indicators_result, daily_candles = await asyncio.gather(
        get_candles_and_indicators(token, symbol),
        fetch_daily_candles(token, symbol, today_ist, today_ist - timedelta(days=10)),
    )
    candles_15m, candles_5m, _, ema20_15m, ema200_15m, ema20_5m, ema200_5m, _, cpr_pivot, cpr_bottom, cpr_top = indicators_result

    # Sort by timestamp ascending so "first of day" is the opening candle
    candles_15m = sorted(candles_15m, key=_candle_sort_key)
    candles_5m = sorted(candles_5m, key=_candle_sort_key)

    _log.debug(
        "Extended context %s: today_ist=%s, 5m count=%s, 15m count=%s",
        symbol, today_ist, len(candles_5m), len(candles_15m),
    )
    if candles_5m:
        sample_dates_5m = {_candle_date_ist(c) for c in candles_5m[:5]} | {_candle_date_ist(c) for c in candles_5m[-5:]}
        _log.debug("5m sample dates: %s", sample_dates_5m)
    if candles_15m:
        sample_dates_15m = {_candle_date_ist(c) for c in candles_15m[:5]} | {_candle_date_ist(c) for c in candles_15m[-5:]}
        _log.debug("15m sample dates: %s", sample_dates_15m)

    candles_5m_today = [c for c in candles_5m if _candle_date_ist(c) == today_ist]
    candles_15m_today = [c for c in candles_15m if _candle_date_ist(c) == today_ist]

    # Previous day high/low/close from DAILY candle. Use trading date (YYYY-MM-DD) so CPR matches actual prev day.
    prev_day_high = prev_day_low = prev_day_close = None
    if daily_candles:
        daily_sorted = sorted(daily_candles, key=_candle_sort_key)
        for c in daily_sorted:
            d = _daily_candle_trading_date(c)
            if d == yesterday_ist:
                prev_day_high = c["high"]
                prev_day_low = c["low"]
                prev_day_close = c["close"]
                break
        if prev_day_close is None:
            prev_before_today = [c for c in daily_sorted if _daily_candle_trading_date(c) and _daily_candle_trading_date(c) < today_ist]
            if prev_before_today:
                prev_candle = prev_before_today[-1]
                prev_day_high = prev_candle["high"]
                prev_day_low = prev_candle["low"]
                prev_day_close = prev_candle["close"]

    # Opening ranges based on 5m candles.
    # Note: Some feeds timestamp 5m bars at the *end* of the interval (09:20 for 09:15–09:20).
    # We prefer the candle at 09:20 for opening 5m, and 09:20/09:25/09:30 for opening 15m.
    range_5m_low = range_5m_high = range_15m_low = range_15m_high = None

    # Use candles from "today" if available; else use latest available session date.
    opening_day = today_ist
    sorted_5m_for_day = sorted(candles_5m_today, key=_candle_sort_key) if candles_5m_today else []
    if not sorted_5m_for_day and candles_5m:
        dates_5m = sorted({_candle_date_ist(c) for c in candles_5m if _candle_date_ist(c)}, reverse=True)
        if dates_5m:
            opening_day = dates_5m[0]
            sorted_5m_for_day = sorted([c for c in candles_5m if _candle_date_ist(c) == opening_day], key=_candle_sort_key)

    if sorted_5m_for_day:
        # Preferred: exact bar timestamped at 09:20 (end of opening 5m)
        win_5 = _candles_at_times_ist(sorted_5m_for_day, opening_day, {dt_time(9, 20)})
        if not win_5:
            # Fallback: treat timestamps as start-of-bar and pick [09:15, 09:20)
            win_5 = _candles_in_window_ist(sorted_5m_for_day, opening_day, OPENING_TIME, dt_time(9, 20))
        if not win_5:
            # fallback: pick candle at/after 9:15
            c0 = _opening_candle_today(sorted_5m_for_day, opening_day)
            win_5 = [c0] if c0 else []
        if win_5:
            range_5m_low = min(c["low"] for c in win_5)
            range_5m_high = max(c["high"] for c in win_5)

        win_15 = _candles_at_times_ist(sorted_5m_for_day, opening_day, {dt_time(9, 20), dt_time(9, 25), dt_time(9, 30)})
        if not win_15:
            # Fallback: treat timestamps as start-of-bar and pick [09:15, 09:30)
            win_15 = _candles_in_window_ist(sorted_5m_for_day, opening_day, OPENING_TIME, dt_time(9, 30))
        if not win_15:
            # fallback: first 3 after 9:15
            after_open = [c for c in sorted_5m_for_day if (_candle_dt_ist(c) and _candle_dt_ist(c).time() >= OPENING_TIME)]
            win_15 = after_open[:3]
        if win_15:
            range_15m_low = min(c["low"] for c in win_15)
            range_15m_high = max(c["high"] for c in win_15)

    # CPR = Central Pivot Range from PREVIOUS trading day's High, Low, Close (from daily candle).
    if prev_day_high is not None and prev_day_low is not None and prev_day_close is not None:
        cpr_pivot, cpr_bottom, cpr_top = _cpr_from_candle({
            "high": prev_day_high, "low": prev_day_low, "close": prev_day_close,
        })

    # Build chart candles: include last 3 calendar days (today, yesterday, day before) so previous days show
    day_before = today_ist - timedelta(days=2)
    chart_dates = {today_ist, yesterday_ist, day_before}
    candles_5m_chart = [c for c in candles_5m if _candle_date_ist(c) in chart_dates]
    if not candles_5m_chart and candles_5m:
        # Fallback: use all dates we have so at least previous days appear
        dates_5m = sorted({_candle_date_ist(c) for c in candles_5m if _candle_date_ist(c)}, reverse=True)
        if dates_5m:
            chart_dates = set(dates_5m[:5])  # up to 5 most recent days
            candles_5m_chart = [c for c in candles_5m if _candle_date_ist(c) in chart_dates]
        if not candles_5m_chart:
            candles_5m_chart = candles_5m  # show all we have
    chart_candles = []
    for c in candles_5m_chart:
        dt = _candle_dt_ist(c)
        if not dt or not _is_market_hours_ist(dt):
            continue
        time_str = dt.strftime("%Y-%m-%dT%H:%M")
        chart_candles.append({
            "time": time_str,
            "open": round(c["open"], 2),
            "high": round(c["high"], 2),
            "low": round(c["low"], 2),
            "close": round(c["close"], 2),
        })

    cpr_width = (cpr_top - cpr_bottom) if (cpr_pivot and cpr_top is not None and cpr_bottom is not None) else None
    cpr_width_pct = (100.0 * cpr_width / cpr_pivot) if (cpr_width and cpr_pivot) else None
    # Narrow CPR: typically < 0.3–0.5% of price → possible big trend; broad → choppy
    cpr_trend_hint = None
    if cpr_width_pct is not None:
        if cpr_width_pct < 0.4:
            cpr_trend_hint = "Narrow – possible big trend"
        else:
            cpr_trend_hint = "Broad – narrow/choppy range"

    return {
        "symbol": symbol.upper(),
        "ema20_15m": round(ema20_15m, 2) if ema20_15m else None,
        "ema200_15m": round(ema200_15m, 2) if ema200_15m else None,
        "ema20_5m": round(ema20_5m, 2) if ema20_5m else None,
        "ema200_5m": round(ema200_5m, 2) if ema200_5m else None,
        "cpr_pivot": round(cpr_pivot, 2) if cpr_pivot is not None else None,
        "cpr_bottom": round(cpr_bottom, 2) if cpr_bottom is not None else None,
        "cpr_top": round(cpr_top, 2) if cpr_top is not None else None,
        "cpr_width": round(cpr_width, 2) if cpr_width is not None else None,
        "cpr_width_pct": round(cpr_width_pct, 3) if cpr_width_pct is not None else None,
        "cpr_trend_hint": cpr_trend_hint,
        "range_5m_low": round(range_5m_low, 2) if range_5m_low is not None else None,
        "range_5m_high": round(range_5m_high, 2) if range_5m_high is not None else None,
        "range_15m_low": round(range_15m_low, 2) if range_15m_low is not None else None,
        "range_15m_high": round(range_15m_high, 2) if range_15m_high is not None else None,
        "prev_day_high": round(prev_day_high, 2) if prev_day_high is not None else None,
        "prev_day_low": round(prev_day_low, 2) if prev_day_low is not None else None,
        "chart_candles": chart_candles,
    }


async def get_chart_data(token: str, symbol: str) -> dict:
    """
    5m candlesticks from yesterday to today with levels for chart overlay.
    Fetches a wider range (last 5 days) then filters to yesterday+today so Upstox returns data.
    Returns: candles (list of {time, open, high, low, close}), cpr_bottom, cpr_pivot, cpr_top,
             prev_day_high, prev_day_low, range_5m_low, range_5m_high, range_15m_low, range_15m_high.
    Time format: "YYYY-MM-DDTHH:mm" IST for lightweight-charts.
    """
    today_ist = _now_ist().date()
    yesterday_ist = today_ist - timedelta(days=1)
    from_date = today_ist - timedelta(days=7)  # 7 days so previous days' 5m candles are returned

    hist_15m, hist_5m, intra_15m, intra_5m, daily_candles = await asyncio.gather(
        fetch_candles(token, symbol, 15, today_ist, from_date),
        fetch_candles(token, symbol, 5, today_ist, from_date),
        fetch_intraday_candles(token, symbol, 15),
        fetch_intraday_candles(token, symbol, 5),
        fetch_daily_candles(token, symbol, today_ist, today_ist - timedelta(days=10)),
    )

    def _merge_sort(*lists: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        for lst in lists:
            for c in lst or []:
                ts = str(c.get("timestamp") or "").strip()
                if not ts:
                    continue
                merged[ts] = c
        return sorted(merged.values(), key=_candle_sort_key)

    # Merge intraday into historical so chart includes today's candles when available
    candles_15m = _merge_sort(hist_15m, intra_15m)
    candles_5m = _merge_sort(hist_5m, intra_5m)

    candles_15m = sorted(candles_15m, key=_candle_sort_key)
    candles_5m = sorted(candles_5m, key=_candle_sort_key)
    # Include last 3 calendar days so chart shows previous days' candlesticks
    day_before = today_ist - timedelta(days=2)
    chart_dates = {today_ist, yesterday_ist, day_before}
    candles_5m_filtered = [c for c in candles_5m if _candle_date_ist(c) in chart_dates]
    if not candles_5m_filtered and candles_5m:
        dates_5m = sorted({_candle_date_ist(c) for c in candles_5m if _candle_date_ist(c)}, reverse=True)
        if dates_5m:
            chart_dates = set(dates_5m[:5])
            candles_5m_filtered = [c for c in candles_5m if _candle_date_ist(c) in chart_dates]
        if not candles_5m_filtered:
            candles_5m_filtered = candles_5m
    candles_5m = candles_5m_filtered

    candles_5m_today = [c for c in candles_5m if _candle_date_ist(c) == today_ist]
    candles_15m_today = [c for c in candles_15m if _candle_date_ist(c) == today_ist]

    prev_day_high = prev_day_low = prev_day_close = None
    if daily_candles:
        daily_sorted = sorted(daily_candles, key=_candle_sort_key)
        for c in daily_sorted:
            if _daily_candle_trading_date(c) == yesterday_ist:
                prev_day_high = c["high"]
                prev_day_low = c["low"]
                prev_day_close = c["close"]
                break
        if prev_day_close is None:
            prev_before_today = [c for c in daily_sorted if _daily_candle_trading_date(c) and _daily_candle_trading_date(c) < today_ist]
            if prev_before_today:
                prev_candle = prev_before_today[-1]
                prev_day_high = prev_candle["high"]
                prev_day_low = prev_candle["low"]
                prev_day_close = prev_candle["close"]

    # CPR from previous day H/L/C (from daily candle, same as extended context)
    cpr_pivot = cpr_bottom = cpr_top = None
    if prev_day_high is not None and prev_day_low is not None and prev_day_close is not None:
        cpr_pivot, cpr_bottom, cpr_top = _cpr_from_candle({
            "high": prev_day_high, "low": prev_day_low, "close": prev_day_close,
        })

    # Opening ranges in exact IST windows (same logic as extended context)
    range_5m_low = range_5m_high = range_15m_low = range_15m_high = None

    opening_day = today_ist
    sorted_5m_for_day = sorted(candles_5m_today, key=_candle_sort_key) if candles_5m_today else []
    if not sorted_5m_for_day and candles_5m:
        dates_5m = sorted({_candle_date_ist(c) for c in candles_5m if _candle_date_ist(c)}, reverse=True)
        if dates_5m:
            opening_day = dates_5m[0]
            sorted_5m_for_day = sorted([c for c in candles_5m if _candle_date_ist(c) == opening_day], key=_candle_sort_key)

    if sorted_5m_for_day:
        win_5 = _candles_at_times_ist(sorted_5m_for_day, opening_day, {dt_time(9, 20)})
        if not win_5:
            win_5 = _candles_in_window_ist(sorted_5m_for_day, opening_day, OPENING_TIME, dt_time(9, 20))
        if not win_5:
            c0 = _opening_candle_today(sorted_5m_for_day, opening_day)
            win_5 = [c0] if c0 else []
        if win_5:
            range_5m_low = min(c["low"] for c in win_5)
            range_5m_high = max(c["high"] for c in win_5)

        win_15 = _candles_at_times_ist(sorted_5m_for_day, opening_day, {dt_time(9, 20), dt_time(9, 25), dt_time(9, 30)})
        if not win_15:
            win_15 = _candles_in_window_ist(sorted_5m_for_day, opening_day, OPENING_TIME, dt_time(9, 30))
        if not win_15:
            after_open = [c for c in sorted_5m_for_day if (_candle_dt_ist(c) and _candle_dt_ist(c).time() >= OPENING_TIME)]
            win_15 = after_open[:3]
        if win_15:
            range_15m_low = min(c["low"] for c in win_15)
            range_15m_high = max(c["high"] for c in win_15)

    chart_candles = []
    for c in candles_5m:
        dt = _candle_dt_ist(c)
        if not dt or not _is_market_hours_ist(dt):
            continue
        time_str = dt.strftime("%Y-%m-%dT%H:%M")
        chart_candles.append({
            "time": time_str,
            "open": round(c["open"], 2),
            "high": round(c["high"], 2),
            "low": round(c["low"], 2),
            "close": round(c["close"], 2),
        })

    return {
        "symbol": symbol.upper(),
        "candles": chart_candles,
        "cpr_pivot": round(cpr_pivot, 2) if cpr_pivot is not None else None,
        "cpr_bottom": round(cpr_bottom, 2) if cpr_bottom is not None else None,
        "cpr_top": round(cpr_top, 2) if cpr_top is not None else None,
        "prev_day_high": round(prev_day_high, 2) if prev_day_high is not None else None,
        "prev_day_low": round(prev_day_low, 2) if prev_day_low is not None else None,
        "range_5m_low": round(range_5m_low, 2) if range_5m_low is not None else None,
        "range_5m_high": round(range_5m_high, 2) if range_5m_high is not None else None,
        "range_15m_low": round(range_15m_low, 2) if range_15m_low is not None else None,
        "range_15m_high": round(range_15m_high, 2) if range_15m_high is not None else None,
    }
