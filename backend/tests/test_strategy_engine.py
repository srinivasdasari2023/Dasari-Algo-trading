"""Tests for strategy engine: bias, no counter-trend."""
import pytest
from datetime import datetime
from app.services.strategy_engine import get_bias, MarketBias
from app.services.market_context import MarketContext


def test_bias_buy():
    assert get_bias(ema20=100, ema200=98) == MarketBias.BUY


def test_bias_sell():
    assert get_bias(ema20=98, ema200=100) == MarketBias.SELL


def test_bias_no_trade():
    assert get_bias(ema20=100, ema200=100) == MarketBias.NO_TRADE
