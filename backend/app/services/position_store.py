"""
In-memory store for open positions and trading history (trades + trailing SL).
Use Redis/PostgreSQL in production.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Literal
import uuid

from app.services.trade_logger import log_trade_close

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class Position:
    id: str
    symbol: str
    option_type: Literal["CE", "PE"]
    side: Literal["BUY", "SELL"]
    quantity: int
    entry_price: float
    sl_trigger: float  # current SL (updated when trailing)
    order_id: str
    created_at: datetime
    # For display: initial SL at order time (first sl_trigger); current is sl_trigger after trails
    initial_sl: float = 0.0


@dataclass
class HistoryEntry:
    id: str
    event_type: Literal["TRADE_OPENED", "SL_TRAILED", "SL_HIT", "TRADE_CLOSED"]
    position_id: str | None
    symbol: str
    at: datetime
    details: str
    old_sl: float | None = None
    new_sl: float | None = None


_positions: dict[str, Position] = {}
_history: list[HistoryEntry] = []


def _now() -> datetime:
    return datetime.now(IST)


def add_position(
    symbol: str,
    option_type: Literal["CE", "PE"],
    side: Literal["BUY", "SELL"],
    quantity: int,
    entry_price: float,
    sl_trigger: float,
    order_id: str,
) -> Position:
    pid = str(uuid.uuid4())[:8]
    pos = Position(
        id=pid,
        symbol=symbol,
        option_type=option_type,
        side=side,
        quantity=quantity,
        entry_price=entry_price,
        sl_trigger=sl_trigger,
        initial_sl=sl_trigger,
        order_id=order_id,
        created_at=_now(),
    )
    _positions[pid] = pos
    _history.append(
        HistoryEntry(
            id=str(uuid.uuid4())[:8],
            event_type="TRADE_OPENED",
            position_id=pid,
            symbol=symbol,
            at=_now(),
            details=f"{side} {quantity} @ {entry_price}, SL {sl_trigger}",
        )
    )
    return pos


def get_positions() -> list[Position]:
    return list(_positions.values())


def get_position(position_id: str) -> Position | None:
    return _positions.get(position_id)


def update_sl(position_id: str, new_sl: float, reason: str = "Trailing SL") -> Position | None:
    pos = _positions.get(position_id)
    if not pos:
        return None
    old_sl = pos.sl_trigger
    pos.sl_trigger = new_sl
    _history.append(
        HistoryEntry(
            id=str(uuid.uuid4())[:8],
            event_type="SL_TRAILED",
            position_id=position_id,
            symbol=pos.symbol,
            at=_now(),
            details=reason,
            old_sl=old_sl,
            new_sl=new_sl,
        )
    )
    return pos


def close_position(position_id: str, reason: Literal["SL_HIT", "TRADE_CLOSED"] = "TRADE_CLOSED", sl_price: float | None = None) -> Position | None:
    pos = _positions.pop(position_id, None)
    if not pos:
        return None
    details = f"Closed at SL {sl_price}" if sl_price is not None else reason
    _history.append(
        HistoryEntry(
            id=str(uuid.uuid4())[:8],
            event_type="SL_HIT" if reason == "SL_HIT" else "TRADE_CLOSED",
            position_id=position_id,
            symbol=pos.symbol,
            at=_now(),
            details=details,
            old_sl=pos.sl_trigger,
            new_sl=sl_price,
        )
    )
    # Log trade close for daily reports. P&L fields can be filled once real fills are wired.
    log_trade_close(
        position_id=position_id,
        symbol=pos.symbol,
        side=pos.side,
        quantity=pos.quantity,
        exit_reason=reason if reason else details,
        exit_index=sl_price,
        exit_premium=None,
        pnl_rupees=None,
        pnl_R=None,
    )
    return pos


def get_history(limit: int = 100) -> list[HistoryEntry]:
    return sorted(_history, key=lambda e: e.at, reverse=True)[:limit]
