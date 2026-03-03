"""Aggregated dashboard data: context + signal + positions + history."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DashboardSnapshot(BaseModel):
    market_bias: str
    signal_status: str
    open_positions_count: int
    daily_trades: int
    daily_loss_stop: bool


@router.get("/snapshot", response_model=DashboardSnapshot)
def get_dashboard_snapshot(symbol: str = "NIFTY"):
    """Single call for dashboard overview."""
    return DashboardSnapshot(
        market_bias="NO_TRADE",
        signal_status="NO_SIGNAL",
        open_positions_count=0,
        daily_trades=0,
        daily_loss_stop=False,
    )
