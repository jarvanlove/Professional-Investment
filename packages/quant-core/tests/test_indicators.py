import numpy as np
import pandas as pd
import pytest

from quant_core.indicators import (
    ma, period_return, realized_vol, drawdown_from_high, last_daily_return,
)


def make_nav(values):
    idx = pd.date_range("2026-01-01", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_ma_basic():
    nav = make_nav(range(1, 31))
    assert ma(nav, 20) == pytest.approx(np.mean(range(11, 31)))


def test_ma_insufficient_raises():
    with pytest.raises(ValueError):
        ma(make_nav([1.0] * 10), 20)


def test_period_return():
    nav = make_nav([100.0] * 60 + [110.0])
    assert period_return(nav, 20) == pytest.approx(0.10)


def test_realized_vol_annualized():
    nav = make_nav((100 * 1.001 ** np.arange(60)).tolist())
    rets = nav.pct_change().dropna().iloc[-20:]
    assert realized_vol(nav, 20) == pytest.approx(rets.std(ddof=1) * np.sqrt(252))


def test_drawdown_from_high_positive_when_below():
    nav = make_nav([100.0] * 15 + [120.0, 110.0, 108.0, 105.0, 90.0])
    # 20日高点=120，最新=90 → 低于高点 25%
    assert drawdown_from_high(nav, 20) == pytest.approx(0.25)


def test_last_daily_return():
    nav = make_nav([100.0, 105.0])
    assert last_daily_return(nav) == pytest.approx(0.05)
