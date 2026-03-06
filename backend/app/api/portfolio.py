"""Portfolio endpoints: holdings/positions from Upstox."""
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel

from app.api.auth import get_upstox_token
from app.services.portfolio_service import (
    fetch_upstox_holdings_meta,
    analyze_intraday_opportunity_15m,
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


class HoldingsOpportunitiesResponse(BaseModel):
    items: list[HoldingOpportunityItem]
    connected: bool = False
    message: str | None = None


@router.get("/holdings/opportunities", response_model=HoldingsOpportunitiesResponse)
async def get_holdings_opportunities(limit: int = 10):
    """Holdings plus a 15m intraday opportunity per holding (top N by value)."""
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

    opps = await asyncio.gather(
        *[analyze_intraday_opportunity_15m(token, str((h.get("instrument_token") or ""))) for h in holdings],
        return_exceptions=True,
    )

    out: list[HoldingOpportunityItem] = []
    for h, opp in zip(holdings, opps, strict=False):
        ts = h.get("tradingsymbol") or h.get("trading_symbol")
        instrument_key = h.get("instrument_token")
        if isinstance(opp, Exception):
            opp = {"status": "NO_SIGNAL", "reason": "Opportunity calc failed"}
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
                status=opp.get("status"),
                direction=opp.get("direction"),
                reason=opp.get("reason"),
                bias=opp.get("bias"),
                pattern=opp.get("pattern"),
                pattern_strength=opp.get("pattern_strength"),
                ema20=opp.get("ema20"),
                ema200=opp.get("ema200"),
                last_15m_time=opp.get("last_15m_time"),
            )
        )
    return HoldingsOpportunitiesResponse(items=out, connected=True, message=None)

