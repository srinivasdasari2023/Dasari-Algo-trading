"""Market context: index price, EMAs, CPR, bias, ranges. Uses Upstox when connected."""
import asyncio
import logging
import urllib.parse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
import httpx

from app.core.config import settings
from app.api.auth import get_upstox_token
from app.services.candle_service import get_extended_market_context, get_chart_data

router = APIRouter()
_log = logging.getLogger(__name__)

# Max time for extended context. Total handler must respond before proxy closes (often ~25–30s).
# Inner Upstox call limited so whole request stays under PROXY_SAFE_TIMEOUT.
EXTENDED_CONTEXT_TIMEOUT_SEC = 14  # inner get_extended_market_context
PROXY_SAFE_TIMEOUT_SEC = 20       # entire request (respond before proxy closes → avoids ECONNRESET)

# Upstox instrument keys for indices (format: exchange|name)
INDEX_KEYS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "SENSEX": "BSE_INDEX|SENSEX",
}


class ChartCandle(BaseModel):
    time: str  # "YYYY-MM-DDTHH:mm"
    open: float
    high: float
    low: float
    close: float


class MarketContextResponse(BaseModel):
    symbol: str
    last_price: float
    ema20_15m: float | None
    ema200_15m: float | None
    cpr_pivot: float | None
    cpr_bottom: float | None
    cpr_top: float | None
    bias: Literal["BUY", "SELL", "NO_TRADE"]
    in_cpr_band: bool
    source: str = "live"  # "live" | "placeholder"


@router.get("/context/{symbol}", response_model=MarketContextResponse)
async def get_market_context(symbol: str):
    """Live market context for dashboard. Symbol: NIFTY | SENSEX. Uses Upstox LTP when connected."""
    symbol_upper = symbol.upper()
    if symbol_upper not in INDEX_KEYS:
        raise HTTPException(status_code=400, detail="Symbol must be NIFTY or SENSEX")

    token = get_upstox_token()
    if not token:
        return MarketContextResponse(
            symbol=symbol_upper,
            last_price=0.0,
            ema20_15m=None,
            ema200_15m=None,
            cpr_pivot=None,
            cpr_bottom=None,
            cpr_top=None,
            bias="NO_TRADE",
            in_cpr_band=False,
            source="placeholder",
        )

    instrument_key = INDEX_KEYS[symbol_upper]
    encoded_key = urllib.parse.quote(instrument_key, safe="")
    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={encoded_key}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            url,
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        )

    if resp.status_code != 200:
        return MarketContextResponse(
            symbol=symbol_upper,
            last_price=0.0,
            ema20_15m=None,
            ema200_15m=None,
            cpr_pivot=None,
            cpr_bottom=None,
            cpr_top=None,
            bias="NO_TRADE",
            in_cpr_band=False,
            source="placeholder",
        )

    try:
        data = resp.json()
        inner = data.get("data", {}) or {}
        quote = inner.get(instrument_key) or inner.get(instrument_key.replace("|", ":")) or {}
        last_price = float(quote.get("last_price", 0) or 0)
    except (ValueError, KeyError, TypeError):
        last_price = 0.0

    return MarketContextResponse(
        symbol=symbol_upper,
        last_price=last_price,
        ema20_15m=None,
        ema200_15m=None,
        cpr_pivot=None,
        cpr_bottom=None,
        cpr_top=None,
        bias="NO_TRADE",
        in_cpr_band=False,
        source="live",
    )


class ExtendedMarketContextResponse(BaseModel):
    symbol: str
    last_price: float
    bias: Literal["BUY", "SELL", "NO_TRADE"]
    source: str
    ema20_15m: float | None = None
    ema200_15m: float | None = None
    ema20_5m: float | None = None
    ema200_5m: float | None = None
    cpr_pivot: float | None = None
    cpr_bottom: float | None = None
    cpr_top: float | None = None
    cpr_width: float | None = None
    cpr_width_pct: float | None = None
    cpr_trend_hint: str | None = None
    range_5m_low: float | None = None
    range_5m_high: float | None = None
    range_15m_low: float | None = None
    range_15m_high: float | None = None
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    chart_candles: list[ChartCandle] | None = None


def _extended_fallback(symbol_upper: str, reason: str = "placeholder") -> ExtendedMarketContextResponse:
    """Return a safe fallback so the UI never gets socket hang up."""
    return ExtendedMarketContextResponse(
        symbol=symbol_upper,
        last_price=0.0,
        bias="NO_TRADE",
        source=reason,
    )


async def _get_extended_context_impl(symbol_upper: str) -> ExtendedMarketContextResponse:
    """Inner implementation so we can enforce a hard timeout and avoid proxy socket hang up."""
    if symbol_upper not in INDEX_KEYS:
        raise HTTPException(status_code=400, detail="Symbol must be NIFTY or SENSEX")

    token = get_upstox_token()
    if not token:
        return _extended_fallback(symbol_upper, "placeholder")

    try:
        base_ctx = await asyncio.wait_for(get_market_context(symbol_upper), timeout=5.0)
    except asyncio.TimeoutError:
        _log.warning("Extended context: get_market_context timed out for %s", symbol_upper)
        return _extended_fallback(symbol_upper, "timeout")
    except Exception as e:
        _log.warning("Extended context: get_market_context failed for %s: %s", symbol_upper, e)
        return _extended_fallback(symbol_upper, "error")

    try:
        extended = await asyncio.wait_for(
            get_extended_market_context(token, symbol_upper),
            timeout=EXTENDED_CONTEXT_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        _log.warning("Extended context: Upstox timed out for %s", symbol_upper)
        return ExtendedMarketContextResponse(
            symbol=symbol_upper,
            last_price=base_ctx.last_price,
            bias=base_ctx.bias,
            source="timeout",
            chart_candles=None,
        )
    except asyncio.CancelledError:
        _log.warning("Extended context: cancelled for %s", symbol_upper)
        return ExtendedMarketContextResponse(
            symbol=symbol_upper,
            last_price=base_ctx.last_price,
            bias=base_ctx.bias,
            source="timeout",
            chart_candles=None,
        )
    except Exception as e:
        _log.warning("Extended context: get_extended_market_context failed for %s: %s", symbol_upper, e)
        return ExtendedMarketContextResponse(
            symbol=symbol_upper,
            last_price=base_ctx.last_price,
            bias=base_ctx.bias,
            source="error",
            chart_candles=None,
        )

    ema20 = extended.get("ema20_15m")
    ema200 = extended.get("ema200_15m")
    if ema20 is not None and ema200 is not None:
        bias = "BUY" if ema20 > ema200 else ("SELL" if ema20 < ema200 else "NO_TRADE")
    else:
        bias = base_ctx.bias

    return ExtendedMarketContextResponse(
        symbol=symbol_upper,
        last_price=base_ctx.last_price,
        bias=bias,
        source=base_ctx.source,
        ema20_15m=extended.get("ema20_15m"),
        ema200_15m=extended.get("ema200_15m"),
        ema20_5m=extended.get("ema20_5m"),
        ema200_5m=extended.get("ema200_5m"),
        cpr_pivot=extended.get("cpr_pivot"),
        cpr_bottom=extended.get("cpr_bottom"),
        cpr_top=extended.get("cpr_top"),
        cpr_width=extended.get("cpr_width"),
        cpr_width_pct=extended.get("cpr_width_pct"),
        cpr_trend_hint=extended.get("cpr_trend_hint"),
        range_5m_low=extended.get("range_5m_low"),
        range_5m_high=extended.get("range_5m_high"),
        range_15m_low=extended.get("range_15m_low"),
        range_15m_high=extended.get("range_15m_high"),
        prev_day_high=extended.get("prev_day_high"),
        prev_day_low=extended.get("prev_day_low"),
        chart_candles=_extended_chart_candles(extended.get("chart_candles")),
    )


@router.get("/context/extended/{symbol}", response_model=ExtendedMarketContextResponse)
async def get_extended_context(symbol: str):
    """Extended market context: LTP, CPR, ranges, EMAs. Always responds within PROXY_SAFE_TIMEOUT to avoid socket hang up."""
    symbol_upper = (symbol or "NIFTY").upper()
    try:
        return await asyncio.wait_for(
            _get_extended_context_impl(symbol_upper),
            timeout=PROXY_SAFE_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        _log.warning("Extended context: full request timed out for %s", symbol_upper)
        return _extended_fallback(symbol_upper, "timeout")
    except asyncio.CancelledError:
        _log.warning("Extended context: request cancelled for %s", symbol_upper)
        return _extended_fallback(symbol_upper, "timeout")
    except HTTPException:
        raise
    except Exception as e:
        _log.exception("Extended context: unhandled error for %s: %s", symbol_upper, e)
        return _extended_fallback(symbol_upper, "error")


def _extended_chart_candles(raw: list | None) -> list[ChartCandle] | None:
    if not raw:
        return None
    out = []
    for c in raw:
        try:
            if isinstance(c, dict) and "time" in c and "open" in c and "high" in c and "low" in c and "close" in c:
                out.append(ChartCandle(**{k: c[k] for k in ("time", "open", "high", "low", "close")}))
        except (TypeError, ValueError, KeyError):
            continue
    return out if out else None


class ChartDataResponse(BaseModel):
    symbol: str
    candles: list[ChartCandle]
    cpr_pivot: float | None = None
    cpr_bottom: float | None = None
    cpr_top: float | None = None
    prev_day_high: float | None = None
    prev_day_low: float | None = None
    range_5m_low: float | None = None
    range_5m_high: float | None = None
    range_15m_low: float | None = None
    range_15m_high: float | None = None


@router.get("/chart/{symbol}", response_model=ChartDataResponse)
async def get_chart(symbol: str):
    """5m candlesticks from yesterday to today with CPR, yesterday H/L, today 5m and 15m opening range."""
    import logging
    _log = logging.getLogger(__name__)
    symbol_upper = symbol.upper()
    if symbol_upper not in INDEX_KEYS:
        raise HTTPException(status_code=400, detail="Symbol must be NIFTY or SENSEX")

    token = get_upstox_token()
    if not token:
        return ChartDataResponse(symbol=symbol_upper, candles=[])

    try:
        data = await get_chart_data(token, symbol_upper)
        candles_out = []
        for c in data.get("candles") or []:
            try:
                if isinstance(c, dict) and "time" in c and "open" in c and "high" in c and "low" in c and "close" in c:
                    candles_out.append(ChartCandle(**{k: c[k] for k in ("time", "open", "high", "low", "close")}))
            except (TypeError, ValueError, KeyError):
                continue
        return ChartDataResponse(
            symbol=data.get("symbol", symbol_upper),
            candles=candles_out,
            cpr_pivot=data.get("cpr_pivot"),
            cpr_bottom=data.get("cpr_bottom"),
            cpr_top=data.get("cpr_top"),
            prev_day_high=data.get("prev_day_high"),
            prev_day_low=data.get("prev_day_low"),
            range_5m_low=data.get("range_5m_low"),
            range_5m_high=data.get("range_5m_high"),
            range_15m_low=data.get("range_15m_low"),
            range_15m_high=data.get("range_15m_high"),
        )
    except Exception as e:
        _log.warning("Chart data failed for %s: %s", symbol_upper, e)
        return ChartDataResponse(symbol=symbol_upper, candles=[])
