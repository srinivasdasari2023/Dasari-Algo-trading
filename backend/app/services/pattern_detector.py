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
