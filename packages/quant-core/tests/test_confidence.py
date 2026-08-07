from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant_core.confidence import compute_confidence


AS_OF = date(2026, 8, 7)


def _nav(days: int, as_of=None, gap_days: int = 0) -> pd.Series:
    as_of = as_of or pd.Timestamp("2026-08-07")
    end = as_of - pd.Timedelta(days=gap_days)
    idx = pd.date_range(end=end, periods=days, freq="D")
    vals = 100 * 1.001 ** np.arange(days)
    return pd.Series(vals, index=idx)


def test_history_length_boundaries():
    assert compute_confidence(_nav(250), used_proxy=False, score=3, as_of=AS_OF).score == pytest.approx(1.0 * 0.8, abs=0.01)
    assert compute_confidence(_nav(120), used_proxy=False, score=3, as_of=AS_OF).score == pytest.approx(0.85 * 0.8, abs=0.01)
    assert compute_confidence(_nav(61), used_proxy=False, score=3, as_of=AS_OF).score == pytest.approx(0.70 * 0.8, abs=0.01)
    assert compute_confidence(_nav(30), used_proxy=False, score=3, as_of=AS_OF).score == pytest.approx(0.4 * 0.8, abs=0.01)


def test_proxy_penalty():
    base = compute_confidence(_nav(120), used_proxy=False, score=3, as_of=AS_OF).score
    proxy = compute_confidence(_nav(120), used_proxy=True, score=3, as_of=AS_OF).score
    assert proxy == pytest.approx(base * 0.8, abs=0.01)


def test_staleness_penalty():
    fresh = compute_confidence(_nav(120, gap_days=0), used_proxy=False, score=3, as_of=AS_OF).score
    stale = compute_confidence(_nav(120, gap_days=5), used_proxy=False, score=3, as_of=AS_OF).score
    assert stale < fresh
    assert stale == pytest.approx(fresh * 0.8, abs=0.01)


def test_signal_strength_factor():
    strong = compute_confidence(_nav(250), used_proxy=False, score=5, as_of=AS_OF).score
    medium = compute_confidence(_nav(250), used_proxy=False, score=3, as_of=AS_OF).score
    assert strong == pytest.approx(1.0, abs=0.01)
    assert medium == pytest.approx(0.8, abs=0.01)


def test_level_thresholds():
    assert compute_confidence(_nav(250), used_proxy=False, score=5, as_of=AS_OF).level == "high"
    assert compute_confidence(_nav(120), used_proxy=False, score=3, as_of=AS_OF).level == "medium"
    assert compute_confidence(_nav(30), used_proxy=False, score=3, as_of=AS_OF).level == "low"
