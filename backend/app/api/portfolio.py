"""Portfolio endpoints: holdings/positions from Upstox."""
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel

from app.api.auth import get_upstox_token
from app.services.portfolio_service import (
    fetch_upstox_holdings_meta,
    analyze_intraday_opportunity_15m,
    analyze_holdings_reduce_buyback,
    record_reduced,
    clear_buyback_done,
)

router = APIRouter()


class HoldingItem(BaseModel):
    isin: str | None = None
    exchange: str | None = None
    tradingsymbol: str | None = None
    company_name: str | None = None
    quantity: int | None = None
    average_price: float | None = None
    last_price: float | None = None
    close_price: float | None = None
    pnl: float | None = None
    day_change: float | None = None
    day_change_percentage: float | None = None
    instrument_token: str | None = None


class HoldingsResponse(BaseModel):
    items: list[HoldingItem]
    connected: bool = False
    message: str | None = None


@router.get("/holdings", response_model=HoldingsResponse)
async def get_holdings():
    """
    Get long-term holdings (stocks) from Upstox demat account.
    Requires Upstox to be connected.
    """
    token = get_upstox_token()
    if not token:
        return HoldingsResponse(items=[], connected=False, message="Upstox not connected")

    meta = await fetch_upstox_holdings_meta(token)
    raw = meta.get("items") or []
    items: list[HoldingItem] = []
    for h in raw:
        if not isinstance(h, dict):
            continue
        # Upstox returns both trading_symbol and tradingsymbol; prefer tradingsymbol if present
        ts = h.get("tradingsymbol") or h.get("trading_symbol")
        items.append(
            HoldingItem(
                isin=h.get("isin"),
                exchange=h.get("exchange"),
                tradingsymbol=ts,
                company_name=h.get("company_name"),
                quantity=h.get("quantity"),
                average_price=h.get("average_price"),
                last_price=h.get("last_price"),
                close_price=h.get("close_price"),
                pnl=h.get("pnl"),
                day_change=h.get("day_change"),
                day_change_percentage=h.get("day_change_percentage"),
                instrument_token=h.get("instrument_token"),
            )
        )
    if not items:
        if meta.get("ok") is False:
            msg = f"Upstox holdings fetch failed (HTTP {meta.get('status_code')})."
        else:
            msg = "Upstox returned 0 long-term holdings."
        return HoldingsResponse(items=[], connected=True, message=msg)
    return HoldingsResponse(items=items, connected=True, message=None)


class HoldingOpportunityItem(HoldingItem):
    status: str | None = None  # SIGNAL | NO_SIGNAL
    direction: str | None = None  # BUY | SELL
    reason: str | None = None
    bias: str | None = None
    pattern: str | None = None
    pattern_strength: float | None = None
    ema20: float | None = None
    ema200: float | None = None
    last_15m_time: str | None = None
    # Reduce / Buy-back strategy
    action: str | None = None  # REDUCE | BUY_BACK | NO_ACTION
    suggested_qty: int | None = None
    reduce_pct: int | None = None


class RecordReducedRequest(BaseModel):
    instrument_key: str
    quantity_sold: int


class BuybackDoneRequest(BaseModel):
    instrument_key: str


class HoldingsOpportunitiesResponse(BaseModel):
    items: list[HoldingOpportunityItem]
    connected: bool = False
    message: str | None = None


@router.get("/holdings/opportunities", response_model=HoldingsOpportunitiesResponse)
async def get_holdings_opportunities(limit: int = 10, reduce_pct: int | None = None):
    """
    Holdings plus 15m opportunity per holding (top N by value).
    If reduce_pct is set (20, 30, or 50), uses reduce-on-weakness / buy-back-on-strength strategy
    and returns action (REDUCE | BUY_BACK | NO_ACTION), suggested_qty, reduce_pct.
    """
    token = get_upstox_token()
    if not token:
        return HoldingsOpportunitiesResponse(items=[], connected=False, message="Upstox not connected")

    meta = await fetch_upstox_holdings_meta(token)
    raw = meta.get("items") or []
    holdings: list[dict] = [h for h in raw if isinstance(h, dict)]
    if not holdings:
        if meta.get("ok") is False:
            msg = f"Upstox holdings fetch failed (HTTP {meta.get('status_code')})."
        else:
            msg = "Upstox returned 0 long-term holdings."
        return HoldingsOpportunitiesResponse(items=[], connected=True, message=msg)

    def value(h: dict) -> float:
        try:
            q = float(h.get("quantity") or 0)
            lp = float(h.get("last_price") or 0)
            return q * lp
        except Exception:
            return 0.0

    holdings = sorted(holdings, key=value, reverse=True)[: max(1, min(int(limit or 10), 25))]

    use_reduce_buyback = reduce_pct is not None and reduce_pct in (20, 30, 50)

    if use_reduce_buyback:
        opps = await asyncio.gather(
            *[
                analyze_holdings_reduce_buyback(
                    token,
                    str((h.get("instrument_token") or "")),
                    int(h.get("quantity") or 0),
                    reduce_pct,
                )
                for h in holdings
            ],
            return_exceptions=True,
        )
    else:
        opps = await asyncio.gather(
            *[analyze_intraday_opportunity_15m(token, str((h.get("instrument_token") or ""))) for h in holdings],
            return_exceptions=True,
        )

    out: list[HoldingOpportunityItem] = []
    for h, opp in zip(holdings, opps, strict=False):
        ts = h.get("tradingsymbol") or h.get("trading_symbol")
        instrument_key = h.get("instrument_token")
        if isinstance(opp, Exception):
            opp = {"status": "NO_SIGNAL", "reason": "Opportunity calc failed", "action": "NO_ACTION", "suggested_qty": 0}
        if use_reduce_buyback:
            action = opp.get("action", "NO_ACTION")
            direction = "SELL" if action == "REDUCE" else ("BUY" if action == "BUY_BACK" else None)
            status = "SIGNAL" if action in ("REDUCE", "BUY_BACK") else "NO_SIGNAL"
        else:
            action = None
            direction = opp.get("direction")
            status = opp.get("status")
        out.append(
            HoldingOpportunityItem(
                isin=h.get("isin"),
                exchange=h.get("exchange"),
                tradingsymbol=ts,
                company_name=h.get("company_name"),
                quantity=h.get("quantity"),
                average_price=h.get("average_price"),
                last_price=h.get("last_price"),
                close_price=h.get("close_price"),
                pnl=h.get("pnl"),
                day_change=h.get("day_change"),
                day_change_percentage=h.get("day_change_percentage"),
                instrument_token=instrument_key,
                status=status,
                direction=direction,
                reason=opp.get("reason"),
                bias=opp.get("bias"),
                pattern=opp.get("pattern"),
                pattern_strength=opp.get("pattern_strength"),
                ema20=opp.get("ema20"),
                ema200=opp.get("ema200"),
                last_15m_time=opp.get("last_15m_time"),
                action=action if use_reduce_buyback else None,
                suggested_qty=opp.get("suggested_qty") if use_reduce_buyback else None,
                reduce_pct=reduce_pct if use_reduce_buyback else None,
            )
        )
    return HoldingsOpportunitiesResponse(items=out, connected=True, message=None)


@router.post("/holdings/reduced")
def post_holdings_reduced(body: RecordReducedRequest):
    """Record that user reduced holding (sold quantity_sold). Used for buy-back suggestion."""
    record_reduced(body.instrument_key, max(0, body.quantity_sold))
    return {"ok": True, "instrument_key": body.instrument_key, "quantity_sold": body.quantity_sold}


@router.post("/holdings/buyback-done")
def post_holdings_buyback_done(body: BuybackDoneRequest):
    """Clear reduced state after user bought back."""
    clear_buyback_done(body.instrument_key)
    return {"ok": True, "instrument_key": body.instrument_key}

