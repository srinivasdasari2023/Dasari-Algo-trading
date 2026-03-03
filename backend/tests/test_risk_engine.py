"""Tests for risk engine: daily limits, 1-loss stop."""
from app.services.risk_engine import check_daily_limits, RiskCheckResult


def test_allowed_when_under_limits():
    r = check_daily_limits(daily_trade_count=1, daily_loss_count=0, max_trades_per_day=3)
    assert r.allowed is True
    assert r.reason == "ok"


def test_rejected_after_one_loss():
    r = check_daily_limits(daily_trade_count=1, daily_loss_count=1, max_trades_per_day=3)
    assert r.allowed is False
    assert r.reason == "daily_loss_stop"


def test_rejected_at_max_trades():
    r = check_daily_limits(daily_trade_count=3, daily_loss_count=0, max_trades_per_day=3)
    assert r.allowed is False
    assert r.reason == "max_trades_per_day"
