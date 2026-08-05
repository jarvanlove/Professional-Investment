# tests/test_scoring.py
import numpy as np
import pandas as pd
import pytest

from quant_core.scoring import trend_score, score_multiplier


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    idx = pd.date_range("2026-01-01", periods=days, freq="B")
    return pd.Series(vals, index=idx)


def test_perfect_uptrend_scores_5():
    # 温和上升：nav>MA20, MA20>MA60, R20>0, R60>0, 偏离在 [-3%,+8%] 内
    assert trend_score(uptrend()) == 5


def test_spike_above_8pct_loses_position_point():
    nav = uptrend()
    nav.iloc[-1] = nav.iloc[-2] * 1.10  # 单日+10%，偏离 MA20 必然 >8%
    assert trend_score(nav) == 4


def test_downtrend_scores_low():
    vals = 100 * 0.998 ** np.arange(80)
    idx = pd.date_range("2026-01-01", periods=80, freq="B")
    nav = pd.Series(vals, index=idx)
    assert trend_score(nav) <= 1


def test_score_multiplier_mapping():
    assert score_multiplier(5) == 1.0
    assert score_multiplier(4) == 0.75
    assert score_multiplier(2) == 0.25
    assert score_multiplier(0) == 0.0
