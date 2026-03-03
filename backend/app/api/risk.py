"""Risk limits and mode. Daily trade count, 1-loss stop, square-off."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

router = APIRouter()


class RiskStatusResponse(BaseModel):
    daily_trades: int
    max_trades_per_day: int
    daily_loss_stop_triggered: bool
    trading_allowed: bool
    reason: str | None = None


class TradingModeResponse(BaseModel):
    mode: Literal["MANUAL", "SEMI_AUTO", "FULL_AUTO"]
    consent_required_for_auto: bool


@router.get("/status", response_model=RiskStatusResponse)
def get_risk_status():
    """Current risk state: trade count, loss stop, whether trading is allowed."""
    # TODO: read from Redis/DB
    return RiskStatusResponse(
        daily_trades=0,
        max_trades_per_day=3,
        daily_loss_stop_triggered=False,
        trading_allowed=True,
        reason=None,
    )


@router.get("/mode", response_model=TradingModeResponse)
def get_trading_mode():
    """Current trading mode. Mode switch requires consent and audit."""
    return TradingModeResponse(mode="MANUAL", consent_required_for_auto=True)


@router.post("/mode")
def set_trading_mode(
    mode: Literal["MANUAL", "SEMI_AUTO", "FULL_AUTO"],
    consent_given: bool = False,
):
    """Switch mode. SEMI_AUTO/FULL_AUTO require consent_given=True and are audited."""
    if mode in ("SEMI_AUTO", "FULL_AUTO") and not consent_given:
        return {"allowed": False, "reason": "Consent required for auto trading"}
    # TODO: persist mode, write audit event
    return {"allowed": True, "mode": mode}
