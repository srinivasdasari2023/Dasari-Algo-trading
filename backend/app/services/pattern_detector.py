"""
Candlestick pattern detector – Bullish and Bearish Engulfing ONLY.
No Doji, Hammer, Shooting Star. Deterministic.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class EngulfingResult:
    direction: Literal["BUY", "SELL"]
    body_ratio: float  # current body vs previous body (strength)


def _is_bullish_engulfing(prev: dict, curr: dict, min_body_ratio: float = 1.2) -> bool:
    """
    Bullish Engulfing: current green candle fully engulfs previous red body.
    curr open <= prev close, curr close >= prev open; curr body >= min_body_ratio * prev body.
    """
    po, ph, pl, pc = prev["open"], prev["high"], prev["low"], prev["close"]
    co, ch, cl, cc = curr["open"], curr["high"], curr["low"], curr["close"]
    if pc >= po:  # previous must be red (close < open)
        return False
    if cc <= co:  # current must be green (close > open)
        return False
    if co > pc or cc < po:
        return False
    prev_body = abs(pc - po)
    curr_body = cc - co
    if prev_body <= 0:
        return False
    return curr_body >= min_body_ratio * prev_body


def _is_bearish_engulfing(prev: dict, curr: dict, min_body_ratio: float = 1.2) -> bool:
    """
    Bearish Engulfing: current red candle fully engulfs previous green body.
    curr open >= prev close, curr close <= prev open; curr body >= min_body_ratio * prev body.
    """
    po, ph, pl, pc = prev["open"], prev["high"], prev["low"], prev["close"]
    co, ch, cl, cc = curr["open"], curr["high"], curr["low"], curr["close"]
    if pc <= po:  # previous must be green
        return False
    if cc >= co:  # current must be red
        return False
    if co < pc or cc > po:
        return False
    prev_body = abs(pc - po)
    curr_body = co - cc
    if prev_body <= 0:
        return False
    return curr_body >= min_body_ratio * prev_body


def detect_engulfing(
    prev_candle: dict,
    curr_candle: dict,
    min_body_ratio: float = 1.2,
) -> EngulfingResult | None:
    """
    Detect Bullish or Bearish Engulfing only. 5-min strong candle in trend direction.
    prev_candle / curr_candle: { open, high, low, close }.
    """
    if prev_candle is None or curr_candle is None:
        return None
    if _is_bullish_engulfing(prev_candle, curr_candle, min_body_ratio):
        prev_body = abs(prev_candle["close"] - prev_candle["open"])
        curr_body = curr_candle["close"] - curr_candle["open"]
        ratio = curr_body / prev_body if prev_body else 0
        return EngulfingResult(direction="BUY", body_ratio=ratio)
    if _is_bearish_engulfing(prev_candle, curr_candle, min_body_ratio):
        prev_body = abs(prev_candle["close"] - prev_candle["open"])
        curr_body = curr_candle["open"] - curr_candle["close"]
        ratio = curr_body / prev_body if prev_body else 0
        return EngulfingResult(direction="SELL", body_ratio=ratio)
    return None


def detect_resistance_rejection(
    prev_candle: dict,
    curr_candle: dict,
    ema20_5m: float,
    tolerance_pct: float = 0.002,
    ema_close_tolerance_pct: float = 0.002,
    recent_high: float | None = None,
) -> bool:
    """
    Bearish: price tested resistance (prior/recent high or EMA20), then rejected — close red and at/near below EMA20.
    recent_high: optional max of last 2–3 candles' highs so we catch rejection at swing high (not only prev candle).
    """
    if not prev_candle or not curr_candle or ema20_5m <= 0:
        return False
    prev_high = float(prev_candle.get("high") or 0)
    co, ch, cl, cc = (
        float(curr_candle.get("open") or 0),
        float(curr_candle.get("high") or 0),
        float(curr_candle.get("low") or 0),
        float(curr_candle.get("close") or 0),
    )
    resistance = max(prev_high, ema20_5m)
    if recent_high is not None and recent_high > 0:
        resistance = max(resistance, recent_high)
    if ch < resistance * (1 - tolerance_pct):
        return False
    if cc >= co:
        return False
    return cc <= ema20_5m * (1 + ema_close_tolerance_pct)


def detect_support_bounce(
    prev_candle: dict,
    curr_candle: dict,
    ema20_5m: float,
    tolerance_pct: float = 0.001,
) -> bool:
    """
    Bullish: price tested support (prior low or near EMA20), then bounced — close green and above EMA20.
    Matches chart: green arrow at support, close above green MA.
    """
    if not prev_candle or not curr_candle or ema20_5m <= 0:
        return False
    prev_low = float(prev_candle.get("low") or 0)
    co, ch, cl, cc = (
        float(curr_candle.get("open") or 0),
        float(curr_candle.get("high") or 0),
        float(curr_candle.get("low") or 0),
        float(curr_candle.get("close") or 0),
    )
    support = min(prev_low, ema20_5m)
    if cl > support * (1 + tolerance_pct):
        return False
    return cc > co and cc > ema20_5m


def detect_cpr_bottom_bounce(
    curr_candle: dict,
    cpr_bottom: float,
    ema20_5m: float,
    tolerance_pct: float = 0.002,
) -> bool:
    """
    BUY: last 5m candle low touched CPR bottom, closed green above CPR bottom or EMA20 (5m).
    """
    if not curr_candle or cpr_bottom is None or cpr_bottom <= 0:
        return False
    co, ch, cl, cc = (
        float(curr_candle.get("open") or 0),
        float(curr_candle.get("high") or 0),
        float(curr_candle.get("low") or 0),
        float(curr_candle.get("close") or 0),
    )
    if cl > cpr_bottom * (1 + tolerance_pct):
        return False
    if cc <= co:
        return False
    return cc > cpr_bottom or (ema20_5m > 0 and cc > ema20_5m)


def detect_cpr_top_rejection(
    curr_candle: dict,
    cpr_top: float,
    ema20_5m: float,
    tolerance_pct: float = 0.002,
    ema_close_tolerance_pct: float = 0.002,
) -> bool:
    """
    SELL: last 5m candle high touched CPR top, closed red below CPR top or EMA20 (5m).
    """
    if not curr_candle or cpr_top is None or cpr_top <= 0:
        return False
    co, ch, cl, cc = (
        float(curr_candle.get("open") or 0),
        float(curr_candle.get("high") or 0),
        float(curr_candle.get("low") or 0),
        float(curr_candle.get("close") or 0),
    )
    if ch < cpr_top * (1 - tolerance_pct):
        return False
    if cc >= co:
        return False
    return cc < cpr_top or (ema20_5m > 0 and cc <= ema20_5m * (1 + ema_close_tolerance_pct))
