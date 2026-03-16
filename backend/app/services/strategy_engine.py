"""
Final Strategy – High-Probability Signals (Option B).
Time 9:20–14:45 IST; no 15m EMA bias; S/R + CPR + engulfing+2m.
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
    """15m EMA20 vs EMA200 (informational only; we do not require bias for signals in Option B)."""
    if ema20 > ema200:
        return MarketBias.BUY
    if ema20 < ema200:
        return MarketBias.SELL
    return MarketBias.NO_TRADE


def is_in_trading_window(ts: datetime | None = None) -> bool:
    """Allowed: 09:20–14:45 IST (9:20 AM to 2:45 PM). Single window."""
    if ts is None:
        ts = datetime.now(IST)
    elif ts.tzinfo is None:
        ts = ts.replace(tzinfo=IST)
    else:
        ts = ts.astimezone(IST)
    t = ts.time()
    window_start = time(9, 20)
    window_end = time(14, 45)  # 2:45 PM
    return window_start <= t <= window_end


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
    resistance_rejection: bool = False,
    support_bounce: bool = False,
    cpr_bottom_bounce: bool = False,
    cpr_top_rejection: bool = False,
) -> SignalResult:
    """
    Final strategy (Option B): time → CPR band filter → pattern (no 15m bias required).
    BUY: CPR bottom bounce, support bounce, or bullish engulfing+2m.
    SELL: CPR top rejection, resistance rejection, or bearish engulfing+2m.
    """
    bias = get_bias(ctx.ema20_15m, ctx.ema200_15m)

    time_ok = is_in_trading_window(ctx.timestamp)
    if not time_ok:
        return SignalResult(
            signal="NO_SIGNAL",
            reason="Outside allowed time window (9:20–14:45 IST)",
            time_window_ok=False,
            bias=bias,
            in_cpr_band=is_price_in_cpr(
                ctx.low, ctx.high, ctx.cpr_bottom, ctx.cpr_top
            ),
            pattern_ok=any(
                [
                    engulfing is not None,
                    resistance_rejection,
                    support_bounce,
                    cpr_bottom_bounce,
                    cpr_top_rejection,
                ]
            ),
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
            pattern_ok=False,
            entry_sequence_ok=False,
        )

    # Path 1: CPR bottom bounce → BUY (no bias required)
    if cpr_bottom_bounce:
        return SignalResult(
            signal="BUY",
            reason="CPR bottom bounce (low at CPR bottom, close green above)",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=True,
            option_instrument_key=None,
        )

    # Path 2: CPR top rejection → SELL (no bias required)
    if cpr_top_rejection:
        return SignalResult(
            signal="SELL",
            reason="CPR top rejection (high at CPR top, close red below)",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=True,
            option_instrument_key=None,
        )

    # Path 3: Support bounce → BUY (no bias required)
    if support_bounce:
        return SignalResult(
            signal="BUY",
            reason="Support bounce (low at support, close green above EMA20)",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=True,
            option_instrument_key=None,
        )

    # Path 4: Resistance rejection → SELL (no bias required)
    if resistance_rejection:
        return SignalResult(
            signal="SELL",
            reason="Resistance rejection (high at resistance, close red below EMA20)",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=True,
            option_instrument_key=None,
        )

    # Path 5: Engulfing + 2m entry → BUY or SELL by engulfing direction (no bias required)
    if engulfing is not None:
        entry_ok = entry_sequence_ok if entry_sequence_ok is not None else False
        if entry_ok:
            return SignalResult(
                signal=engulfing.direction,
                reason="Engulfing + 2m entry confirmation",
                time_window_ok=True,
                bias=bias,
                in_cpr_band=False,
                pattern_ok=True,
                entry_sequence_ok=True,
                option_instrument_key=None,
            )
        return SignalResult(
            signal="NO_SIGNAL",
            reason="Engulfing present but entry sequence not satisfied",
            time_window_ok=True,
            bias=bias,
            in_cpr_band=False,
            pattern_ok=True,
            entry_sequence_ok=False,
        )

    return SignalResult(
        signal="NO_SIGNAL",
        reason="No pattern (S/R, CPR, or engulfing+entry)",
        time_window_ok=True,
        bias=bias,
        in_cpr_band=False,
        pattern_ok=False,
        entry_sequence_ok=False,
    )
