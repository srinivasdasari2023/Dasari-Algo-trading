"""Market context dataclass: EMAs, CPR, OHLC. Used by strategy engine."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketContext:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    ema20_15m: float
    ema200_15m: float
    ema20_5m: float | None
    ema20_2m: float | None
    cpr_pivot: float | None
    cpr_bottom: float | None
    cpr_top: float | None
