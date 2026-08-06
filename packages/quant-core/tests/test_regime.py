# tests/test_regime.py
from quant_core.regime import market_regime


def test_defensive_on_big_drawdown():
    assert market_regime({"a": 5, "b": 5, "c": 5}, portfolio_dd=0.13, peak_profit_rate=0.0) == "defensive"


def test_defensive_on_two_weak_tech():
    assert market_regime({"a": 2, "b": 1, "c": 5}, portfolio_dd=0.02, peak_profit_rate=0.0) == "defensive"


def test_protect_on_profit_pullback():
    assert market_regime({"a": 4, "b": 4, "c": 3}, portfolio_dd=0.05, peak_profit_rate=0.09) == "protect"


def test_offensive_when_strong():
    assert market_regime({"a": 4, "b": 5, "c": 3}, portfolio_dd=0.02, peak_profit_rate=0.0) == "offensive"


def test_neutral_default():
    assert market_regime({"a": 3, "b": 4, "c": 2}, portfolio_dd=0.02, peak_profit_rate=0.0) == "neutral"


def test_defensive_beats_offensive():
    assert market_regime({"a": 5, "b": 5, "c": 5}, portfolio_dd=0.13, peak_profit_rate=0.0) == "defensive"
