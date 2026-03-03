"""Signal evaluation and status. Fetches candles, runs strategy, returns signal."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.api.auth import get_upstox_token
from app.services.candle_service import get_candles_and_indicators
from app.services.market_context import MarketContext
from app.services.pattern_detector import detect_engulfing
from app.services.strategy_engine import evaluate
from app.services.risk_engine import check_daily_limits
from app.services.email_service import notify_signal

router = APIRouter()
# IST = UTC+5:30 (no zoneinfo/tzdata dependency on Windows)
IST = timezone(timedelta(hours=5, minutes=30))

# In-memory signal history (last N); use DB in production
_signal_history: list[dict] = []
_SIGNAL_HISTORY_MAX = 100


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

    if not candles_5m:
        return SignalResponse(
            signal_id=None,
            status="NO_SIGNAL",
            reason="No 5m candle data (market may be closed)",
            time_window_ok=False,
            risk_checklist=[],
        )

    # Build context from latest 5m candle
    last_5 = candles_5m[-1]
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
    if len(candles_5m) >= 2:
        prev_5 = candles_5m[-2]
        engulfing = detect_engulfing(prev_5, last_5)

    # Entry sequence: last two 2m candles
    entry_ok = False
    if len(candles_2m) >= 2 and engulfing:
        pullback = candles_2m[-2]
        next_c = candles_2m[-1]
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

    # Run strategy
    result = evaluate(ctx, engulfing, entry_sequence_ok=entry_ok)
    risk_checklist.append(RiskCheckItem(rule="time_window", passed=result.time_window_ok, reason=None))
    risk_checklist.append(RiskCheckItem(rule="bias", passed=result.bias.value != "NO_TRADE", reason=result.reason))
    risk_checklist.append(RiskCheckItem(rule="cpr_filter", passed=not result.in_cpr_band, reason=None))
    risk_checklist.append(RiskCheckItem(rule="engulfing", passed=result.pattern_ok, reason=None))
    risk_checklist.append(RiskCheckItem(rule="entry_sequence", passed=result.entry_sequence_ok, reason=None))

    if result.signal in ("BUY", "SELL"):
        notify_signal(symbol_upper, result.signal, result.reason)

    resp = SignalResponse(
        signal_id=None,
        status=result.signal,
        reason=result.reason,
        time_window_ok=result.time_window_ok,
        risk_checklist=risk_checklist,
        option_instrument_key=result.option_instrument_key,
        rejected=False,
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
