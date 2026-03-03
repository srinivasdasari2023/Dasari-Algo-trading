"""
Risk Engine: daily limits, 1-loss stop, time filter, square-off.
Strict capital preservation. State in Redis/DB.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class RiskCheckResult:
    allowed: bool
    reason: str
    daily_trade_count: int
    daily_loss_count: int
    max_trades_per_day: int = 3


def check_daily_limits(
    daily_trade_count: int,
    daily_loss_count: int,
    max_trades_per_day: int = 3,
) -> RiskCheckResult:
    """
    Max 3 trades per day. 1 loss → stop trading for the day.
    """
    if daily_loss_count >= 1:
        return RiskCheckResult(
            allowed=False,
            reason="daily_loss_stop",
            daily_trade_count=daily_trade_count,
            daily_loss_count=daily_loss_count,
            max_trades_per_day=max_trades_per_day,
        )
    if daily_trade_count >= max_trades_per_day:
        return RiskCheckResult(
            allowed=False,
            reason="max_trades_per_day",
            daily_trade_count=daily_trade_count,
            daily_loss_count=daily_loss_count,
            max_trades_per_day=max_trades_per_day,
        )
    return RiskCheckResult(
        allowed=True,
        reason="ok",
        daily_trade_count=daily_trade_count,
        daily_loss_count=daily_loss_count,
        max_trades_per_day=max_trades_per_day,
    )


def is_after_entry_cutoff(current_time_ist: str, cutoff: str = "12:30") -> bool:
    """Entry cutoff 12:30. No new entries after."""
    # Compare "HH:MM" IST
    return current_time_ist >= cutoff


def is_square_off_time(current_time_ist: str, square_off: str = "15:15") -> bool:
    """Auto square-off at 15:15."""
    return current_time_ist >= square_off
