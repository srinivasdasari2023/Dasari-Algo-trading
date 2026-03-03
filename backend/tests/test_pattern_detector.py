"""Tests for engulfing pattern detector. Deterministic."""
import pytest
from app.services.pattern_detector import detect_engulfing, EngulfingResult


def test_bullish_engulfing():
    prev = {"open": 100, "high": 102, "low": 99, "close": 99.5}
    curr = {"open": 99, "high": 104, "low": 98.5, "close": 103}
    r = detect_engulfing(prev, curr)
    assert r is not None
    assert r.direction == "BUY"
    assert r.body_ratio >= 1.0


def test_bearish_engulfing():
    prev = {"open": 99, "high": 103, "low": 98.5, "close": 102.5}
    curr = {"open": 102, "high": 102.5, "low": 97, "close": 98}
    r = detect_engulfing(prev, curr)
    assert r is not None
    assert r.direction == "SELL"
    assert r.body_ratio >= 1.0


def test_no_engulfing_returns_none():
    prev = {"open": 100, "high": 101, "low": 99, "close": 100.5}
    curr = {"open": 100.5, "high": 101, "low": 100, "close": 100.8}
    r = detect_engulfing(prev, curr)
    assert r is None


def test_none_candles_return_none():
    assert detect_engulfing(None, {"open": 1, "high": 2, "low": 0.5, "close": 1.5}) is None
    assert detect_engulfing({"open": 1, "high": 2, "low": 0.5, "close": 1.5}, None) is None
