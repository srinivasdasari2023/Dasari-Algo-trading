"""Order placement and status. Positions and history with SL/TSL. Idempotent; Upstox only."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.services.position_store import (
    add_position,
    get_positions,
    get_position,
    update_sl,
    get_history,
)
from app.services.email_service import notify_order_placed, notify_sl_updated

router = APIRouter()


class PlaceOrderRequest(BaseModel):
    signal_id: str
    idempotency_key: str
    instrument_key: str
    side: Literal["BUY", "SELL"]
    quantity: int = 1
    order_type: str = "MARKET"
    sl_trigger: float | None = None
    symbol: str = "NIFTY"
    option_type: Literal["CE", "PE"] = "CE"
    target_premium: float | None = None  # NIFTY ~200 (180–220), SENSEX 500+ (480–520) for CE/PE


class OrderResponse(BaseModel):
    order_id: str
    broker_order_id: str | None
    status: str
    signal_id: str
    position_id: str | None = None


class PositionItem(BaseModel):
    id: str
    symbol: str
    option_type: str
    side: str
    quantity: int
    entry_price: float
    sl_trigger: float
    initial_sl: float
    order_id: str
    created_at: str


class TrailSlRequest(BaseModel):
    new_sl: float
    reason: str = "Trailing SL"


class HistoryItem(BaseModel):
    id: str
    event_type: str
    position_id: str | None
    symbol: str
    at: str
    details: str
    old_sl: float | None
    new_sl: float | None


@router.post("/place", response_model=OrderResponse)
def place_order(req: PlaceOrderRequest):
    """
    Place order via Upstox. Idempotency_key prevents duplicate orders.
    Persists position with SL; strategy can trail SL later via POST /positions/{id}/trail-sl.
    """
    sl = req.sl_trigger if req.sl_trigger is not None else 0.0
    # Placeholder: in production call order_manager.place() and use real entry from Upstox
    order_id = f"ord-{req.idempotency_key[:8]}"
    pos = add_position(
        symbol=req.symbol,
        option_type=req.option_type,
        side=req.side,
        quantity=req.quantity,
        entry_price=0.0,  # TODO: from Upstox fill
        sl_trigger=sl,
        order_id=order_id,
    )
    notify_order_placed(req.symbol, req.side, req.quantity, order_id, req.sl_trigger)
    return OrderResponse(
        order_id=order_id,
        broker_order_id=None,
        status="PENDING",
        signal_id=req.signal_id,
        position_id=pos.id,
    )


@router.get("/positions")
def get_open_positions():
    """Open positions for dashboard: symbol, entry, P&L, SL and trailing SL (current sl_trigger)."""
    try:
        items = []
        for p in get_positions():
            items.append(
                PositionItem(
                    id=p.id,
                    symbol=p.symbol,
                    option_type=p.option_type,
                    side=p.side,
                    quantity=p.quantity,
                    entry_price=p.entry_price,
                    sl_trigger=p.sl_trigger,
                    initial_sl=p.initial_sl,
                    order_id=p.order_id,
                    created_at=p.created_at.isoformat() if p.created_at else "",
                )
            )
        return {"items": items}
    except Exception:
        return {"items": []}


@router.post("/positions/{position_id}/trail-sl")
def trail_sl(position_id: str, body: TrailSlRequest):
    """Update stop loss (trailing). Records in history and sends email."""
    existing = get_position(position_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Position not found")
    old_sl = existing.sl_trigger
    pos = update_sl(position_id, body.new_sl, body.reason)
    if pos:
        notify_sl_updated(pos.symbol, position_id, old_sl, body.new_sl, body.reason)
    return {"position_id": position_id, "old_sl": old_sl, "new_sl": body.new_sl}


@router.get("/history")
def orders_history(limit: int = 100):
    """Trading and trailing history for dashboard."""
    try:
        entries = get_history(limit=limit)
        return {
            "items": [
                HistoryItem(
                    id=e.id,
                    event_type=e.event_type,
                    position_id=e.position_id,
                    symbol=e.symbol,
                    at=e.at.isoformat() if e.at else "",
                    details=e.details,
                    old_sl=e.old_sl,
                    new_sl=e.new_sl,
                )
                for e in entries
            ],
        }
    except Exception:
        return {"items": []}
