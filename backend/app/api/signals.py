"""Signal evaluation and status. Fetches candles, runs strategy, returns signal."""
import asyncio
from datetime import datetime, timezone, timedelta, time as dt_time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.api.auth import get_upstox_token
from app.services.candle_service import get_candles_and_indicators
from app.services.market_context import MarketContext
from app.services.pattern_detector import (
    detect_engulfing,
    detect_resistance_rejection,
    detect_support_bounce,
    detect_cpr_bottom_bounce,
    detect_cpr_top_rejection,
)
from app.services.strategy_engine import evaluate
from app.services.risk_engine import check_daily_limits
from app.services.email_service import notify_signal

router = APIRouter()
# IST = UTC+5:30 (no zoneinfo/tzdata dependency on Windows)
IST = timezone(timedelta(hours=5, minutes=30))

# In-memory signal history (last N); use DB in production
_signal_history: list[dict] = []
_SIGNAL_HISTORY_MAX = 100

# NSE market hours IST (avoid cross-day pattern issues at session open/close)
MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)

# Max time for signal evaluation (Upstox can be slow); respond before proxy socket hang up
SIGNAL_EVALUATE_TIMEOUT_SEC = 22


def _is_market_hours_ist(ts: datetime) -> bool:
    dt = ts.astimezone(IST) if ts.tzinfo else ts.replace(tzinfo=IST)
    t = dt.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


class RiskCheckItem(BaseModel):
    rule: str
    passed: bool
    reason: str | None = None


class SignalResponse(BaseModel):
    signal_id: str | None
    status: Literal["BUY", "SELL", "NO_SIGNAL"]
    reason: str
    time_window_ok: bool
    risk_checklist: list[RiskCheckItem]
    option_instrument_key: str | None = None
    rejected: bool = False
    rejected_reason: str | None = None
    suggested_sl_price: float | None = None   # index level for SL (use with order)
    suggested_target_price: float | None = None  # index level for book profit (or use target premium)


def _parse_ts(ts: str) -> datetime:
    try:
        if isinstance(ts, datetime):
            return ts.astimezone(IST) if ts.tzinfo else ts.replace(tzinfo=IST)
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(IST)
    except (TypeError, ValueError):
        return datetime.now(IST)


@router.get("/evaluate/{symbol}", response_model=SignalResponse)
async def evaluate_signal(symbol: str):
    """
    Evaluate Trend-Continuation Capital Preserver for symbol.
    Fetches 15m/5m/2m candles from Upstox, computes EMAs/CPR, runs strategy and risk check.
    """
    symbol_upper = symbol.upper()
    if symbol_upper not in ("NIFTY", "SENSEX"):
        raise HTTPException(status_code=400, detail="Symbol must be NIFTY or SENSEX")

    token = get_upstox_token()
    if not token:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="Upstox not connected",
            time_window_ok=False,
            risk_checklist=[RiskCheckItem(rule="upstox_connected", passed=False, reason="Connect Upstox first")],
        )

    try:
        return await asyncio.wait_for(
            _evaluate_impl(token, symbol_upper),
            timeout=SIGNAL_EVALUATE_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="Evaluation timed out (Upstox slow)",
            time_window_ok=False,
            risk_checklist=[],
        )
    except Exception:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="Evaluation failed",
            time_window_ok=False,
            risk_checklist=[],
        )


async def _evaluate_impl(token: str, symbol_upper: str) -> SignalResponse:
    """Inner implementation so we can apply a timeout and avoid proxy socket hang up."""
    try:
        (
            candles_15m,
            candles_5m,
            candles_2m,
            ema20_15m,
            ema200_15m,
            ema20_5m,
            ema200_5m,
            ema20_2m,
            cpr_pivot,
            cpr_bottom,
            cpr_top,
        ) = await get_candles_and_indicators(token, symbol_upper)
    except Exception:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="Failed to fetch candles from Upstox",
            time_window_ok=False,
            risk_checklist=[],
        )

    # Filter to today's 5m candles within market hours (IST) so we don't
    # accidentally compare yesterday's last candle with today's first candle.
    today_ist = datetime.now(IST).date()
    candles_5m_today: list[dict] = []
    for c in candles_5m or []:
        ts_c = _parse_ts(c.get("timestamp"))
        if ts_c.date() == today_ist and _is_market_hours_ist(ts_c):
            candles_5m_today.append(c)

    if not candles_5m_today:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="No 5m candle data for today yet (market may be closed)",
            time_window_ok=False,
            risk_checklist=[],
        )

    # Build context from latest 5m candle
    last_5 = candles_5m_today[-1]
    ts = _parse_ts(last_5["timestamp"])
    ctx = MarketContext(
        symbol=symbol_upper,
        timestamp=ts,
        open=last_5["open"],
        high=last_5["high"],
        low=last_5["low"],
        close=last_5["close"],
        volume=last_5["volume"],
        ema20_15m=ema20_15m,
        ema200_15m=ema200_15m,
        ema20_5m=ema20_5m,
        ema20_2m=ema20_2m,
        cpr_pivot=cpr_pivot,
        cpr_bottom=cpr_bottom,
        cpr_top=cpr_top,
    )

    # Engulfing on last two 5m candles
    engulfing = None
    prev_5 = candles_5m_today[-2] if len(candles_5m_today) >= 2 else None
    if prev_5 is not None:
        engulfing = detect_engulfing(prev_5, last_5)

    # S/R and CPR patterns (5m); all use last candle
    ema20_5m_val = float(ema20_5m or 0)
    resistance_rejection = False
    support_bounce = False
    cpr_bottom_bounce = False
    cpr_top_rejection = False
    if prev_5 is not None and ema20_5m_val > 0:
        recent_high = None
        if len(candles_5m_today) >= 3:
            recent_high = max(
                float(c.get("high") or 0) for c in candles_5m_today[-3:]
            )
        resistance_rejection = detect_resistance_rejection(
            prev_5, last_5, ema20_5m_val, recent_high=recent_high
        )
        support_bounce = detect_support_bounce(prev_5, last_5, ema20_5m_val)
    if cpr_bottom is not None and cpr_top is not None:
        cpr_bottom_bounce = detect_cpr_bottom_bounce(
            last_5, float(cpr_bottom), ema20_5m_val
        )
        cpr_top_rejection = detect_cpr_top_rejection(
            last_5, float(cpr_top), ema20_5m_val
        )

    # Entry sequence: last two 2m candles (for engulfing path only)
    entry_ok = False
    if engulfing:
        candles_2m_today: list[dict] = []
        for c in candles_2m or []:
            ts2 = _parse_ts(c.get("timestamp"))
            if ts2.date() == today_ist and _is_market_hours_ist(ts2):
                candles_2m_today.append(c)

        if len(candles_2m_today) >= 2:
            pullback = candles_2m_today[-2]
            next_c = candles_2m_today[-1]
            from app.services.strategy_engine import check_entry_sequence
            entry_ok = check_entry_sequence(pullback, next_c, ema20_2m, engulfing.direction)

    # Risk: daily limits (placeholder counts until we have DB)
    risk_result = check_daily_limits(daily_trade_count=0, daily_loss_count=0)
    risk_checklist = [
        RiskCheckItem(rule="daily_loss_stop", passed=risk_result.allowed or risk_result.reason != "daily_loss_stop", reason=risk_result.reason),
        RiskCheckItem(rule="max_trades_per_day", passed=risk_result.allowed or risk_result.reason != "max_trades_per_day", reason=risk_result.reason),
    ]
    if not risk_result.allowed:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason=f"Risk: {risk_result.reason}",
            time_window_ok=True,
            risk_checklist=risk_checklist,
            rejected=True,
            rejected_reason=risk_result.reason,
        )

    # Run final strategy (Option B: no bias; S/R + CPR + engulfing+2m)
    result = evaluate(
        ctx,
        engulfing,
        entry_sequence_ok=entry_ok,
        resistance_rejection=resistance_rejection,
        support_bounce=support_bounce,
        cpr_bottom_bounce=cpr_bottom_bounce,
        cpr_top_rejection=cpr_top_rejection,
    )
    risk_checklist.append(RiskCheckItem(rule="time_window", passed=result.time_window_ok, reason=None))
    risk_checklist.append(RiskCheckItem(rule="bias", passed=result.bias.value != "NO_TRADE", reason=result.reason))
    risk_checklist.append(RiskCheckItem(rule="cpr_filter", passed=not result.in_cpr_band, reason=None))
    risk_checklist.append(RiskCheckItem(rule="pattern", passed=result.pattern_ok, reason=None))
    risk_checklist.append(RiskCheckItem(rule="entry_sequence", passed=result.entry_sequence_ok, reason=None))

    if result.signal in ("BUY", "SELL"):
        notify_signal(symbol_upper, result.signal, result.reason)

    # Suggested SL and book-profit (index level) from signal candle
    suggested_sl: float | None = None
    suggested_target: float | None = None
    if result.signal == "BUY":
        low_, close_ = last_5["low"], last_5["close"]
        buffer = 10.0 if symbol_upper == "SENSEX" else 5.0
        suggested_sl = low_ - buffer
        r = max(close_ - low_, 1.0)
        suggested_target = close_ + 2.0 * r  # 2R
    elif result.signal == "SELL":
        high_, close_ = last_5["high"], last_5["close"]
        buffer = 10.0 if symbol_upper == "SENSEX" else 5.0
        suggested_sl = high_ + buffer
        r = max(high_ - close_, 1.0)
        suggested_target = close_ - 2.0 * r  # 2R

    resp = SignalResponse(
        signal_id=None,
        status=result.signal,
        reason=result.reason,
        time_window_ok=result.time_window_ok,
        risk_checklist=risk_checklist,
        option_instrument_key=result.option_instrument_key,
        rejected=False,
        suggested_sl_price=suggested_sl,
        suggested_target_price=suggested_target,
    )
    # Persist to in-memory history for dashboard
    _signal_history.append({
        "symbol": symbol_upper,
        "status": resp.status,
        "reason": resp.reason,
        "at": datetime.now(IST).isoformat(),
    })
    if len(_signal_history) > _SIGNAL_HISTORY_MAX:
        _signal_history.pop(0)
    return resp


@router.get("/history")
def signal_history(limit: int = 50):
    """Paginated signal history for dashboard (in-memory; use DB in production)."""
    items = list(_signal_history)[-(limit or 50) :]
    items.reverse()
    return {"items": items, "total": len(_signal_history)}
