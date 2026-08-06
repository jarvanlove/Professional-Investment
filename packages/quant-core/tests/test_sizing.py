# tests/test_sizing.py
import pytest

from quant_core.config import FUNDS, TECH_CODES
from quant_core.sizing import vol_multiplier, base_weight, target_weight
from quant_core.constraints import apply_caps


def test_vol_multiplier_tech_bands():
    bands = FUNDS["001480"].vol_bands
    assert vol_multiplier(0.25, bands) == 1.0
    assert vol_multiplier(0.35, bands) == 0.75
    assert vol_multiplier(0.50, bands) == 0.50
    assert vol_multiplier(0.70, bands) == 0.25


def test_vol_multiplier_dividend_bands():
    bands = FUNDS["005052"].vol_bands
    assert vol_multiplier(0.10, bands) == 1.0
    assert vol_multiplier(0.20, bands) == 0.75
    assert vol_multiplier(0.25, bands) == 0.50
    assert vol_multiplier(0.35, bands) == 0.25


def test_target_weight_example_a():
    # PDF 算例A：中性，财通4分 → 25%×75%×1.0 = 18.75%
    assert target_weight("neutral", "001480", score=4, vol=0.20) == pytest.approx(0.1875)
    assert target_weight("neutral", "025343", score=3, vol=0.20) == pytest.approx(0.075)
    assert target_weight("neutral", "027521", score=2, vol=0.20) == pytest.approx(0.025)
    assert target_weight("neutral", "005052", score=4, vol=0.10) == pytest.approx(0.1875)


def test_target_weight_never_exceeds_cap():
    assert target_weight("offensive", "001480", score=5, vol=0.20) <= 0.30


def test_apply_caps_scales_tech_bucket():
    weights = {"001480": 0.30, "025343": 0.20, "027521": 0.10, "005052": 0.25}
    out = apply_caps(weights, "offensive")
    assert out == weights
    over = {"001480": 0.35, "025343": 0.25, "027521": 0.10, "005052": 0.20}
    out = apply_caps(over, "offensive")
    assert out["001480"] <= 0.30
    assert sum(out[c] for c in TECH_CODES) <= 0.60 + 1e-9
