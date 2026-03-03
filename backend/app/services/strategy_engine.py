"""
Trend-Continuation Capital Preserver – Strategy Engine.
Deterministic: same inputs → same output. No counter-trend; engulfing only.
"""
from dataclasses import dataclass
from datetime import datetime, time, timezone, timedelta
from enum import Enum
from typing import Literal

from app.services.pattern_detector import detect_engulfing, EngulfingResult
from app.services.market_context import MarketContext

# IST = UTC+5:30 (no zoneinfo/tzdata dependency on Windows)
IST = timezone(timedelta(hours=5, minutes=30))


class MarketBias(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


@dataclass
class SignalResult:
    signal: Literal["BUY", "SELL", "NO_SIGNAL"]
    reason: str
    time_window_ok: bool
    bias: MarketBias
    in_cpr_band: bool
    pattern_ok: bool
    entry_sequence_ok: bool
    option_instrument_key: str | None = None


def get_bias(ema20: float, ema200: float) -> MarketBias:
    """15-min EMA20 > EMA200 → BUY only; EMA20 < EMA200 → SELL only; else NO_TRADE."""
    if ema20 > ema200:
        return MarketBias.BUY
    if ema20 < ema200:
        return MarketBias.SELL
    return MarketBias.NO_TRADE


def is_in_trading_window(ts: datetime | None = None) -> bool:
    """Allowed: 09:20–10:30 and 11:15–12:30 IST. Entry cutoff 12:30."""
    if ts is None:
        ts = datetime.now(IST)
    elif ts.tzinfo is None:
        ts = ts.replace(tzinfo=IST)
    else:
        ts = ts.astimezone(IST)
    t = ts.time()
    slot1_start = time(9, 20)
    slot1_end = time(10, 30)
    slot2_start = time(11, 15)
    slot2_end = time(12, 30)
    return (slot1_start <= t <= slot1_end) or (slot2_start <= t <= slot2_end)


def is_price_in_cpr(low: float, high: float, cpr_bottom: float, cpr_top: float) -> bool:
    """Price inside CPR band → no trade (chop avoidance)."""
    if cpr_bottom is None or cpr_top is None:
        return False
    return not (high < cpr_bottom or low > cpr_top)


def check_entry_sequence(
    pullback_candle: dict,
    next_candle: dict,
    ema20_2m: float,
    direction: Literal["BUY", "SELL"],
) -> bool:
    """
    2-min pullback (1 candle) then next 2-min close above/below pullback high/low;
    next close must be above (BUY) or below (SELL) EMA20.
    """
    if direction == "BUY":
        return (
            next_candle["close"] > pullback_candle["high"]
            and next_candle["close"] > ema20_2m
        )
    return (
        next_candle["close"] < pullback_candle["low"]
        and next_candle["close"] < ema20_2m
    )


def evaluate(
    ctx: MarketContext,
    engulfing: EngulfingResult | None,
    entry_sequence_ok: bool | None = None,
) -> SignalResult:
    """
    Full evaluation: bias → time → CPR → engulfing → entry sequence → option filter.
    Returns NO_SIGNAL with reason if any filter fails.
    """
    bias = get_bias(ctx.ema20_15m, ctx.ema200_15m)
    if bias == MarketBias.NO_TRADE:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="No trend bias (EMA20 vs EMA200)",
            time_window_ok=is_in_trading_window(ctx.timestamp),
            bias=bias,
            in_cpr_band=is_price_in_cpr(
                ctx.low, ctx.high, ctx.cpr_bottom, ctx.cpr_top
            ),
            pattern_ok=False,
            entry_sequence_ok=False,
        )

    time_ok = is_in_trading_window(ctx.timestamp)
    if not time_ok:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="Outside allowed time window",
            time_window_ok=False,
            bias=bias,
            in_cpr_band=is_price_in_cpr(
                ctx.low, ctx.high, ctx.cpr_bottom, ctx.cpr_top
            ),
            pattern_ok=engulfing is not None,
            entry_sequence_ok=False,
        )

    in_cpr = is_price_in_cpr(ctx.low, ctx.high, ctx.cpr_bottom, ctx.cpr_top)
    if in_cpr:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="Price inside CPR band (chop filter)",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=True,
            pattern_ok=engulfing is not None,
            entry_sequence_ok=False,
        )

    if engulfing is None or engulfing.direction != bias.value:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="No valid engulfing in trend direction",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=False,
            entry_sequence_ok=False,
        )

    entry_ok = entry_sequence_ok if entry_sequence_ok is not None else False
    if not entry_ok:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="Entry sequence not satisfied",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=False,
        )

    return SignalResult(
        signal=bias.value,
        reason="Trend continuation with engulfing and entry confirmation",
        time_window_ok=True,
        bias=bias,
        in_cpr_band=False,
        pattern_ok=True,
        entry_sequence_ok=True,
        option_instrument_key=None,  # from option filter
    )
