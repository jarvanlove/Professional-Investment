from quant_core.config import (
    FUNDS, TECH_CODES, REGIME_WEIGHTS, REGIME_CASH_MIN,
    SCORE_MULTIPLIERS, UNIT_LIMITS, TECH_TOTAL_CAP,
)


def test_four_funds_present():
    assert set(FUNDS) == {"001480", "025343", "027521", "005052"}


def test_tech_bucket_membership():
    assert set(TECH_CODES) == {"001480", "025343", "027521"}
    assert FUNDS["005052"].bucket == "dividend"


def test_neutral_weights_sum_tech_50_dividend_25():
    w = REGIME_WEIGHTS["neutral"]
    assert sum(w[c] for c in TECH_CODES) == 0.50
    assert w["005052"] == 0.25


def test_caps_match_pdf():
    assert FUNDS["001480"].cap == 0.30
    assert FUNDS["025343"].cap == 0.20
    assert FUNDS["027521"].cap == 0.10
    assert FUNDS["005052"].cap == 0.25
    assert TECH_TOTAL_CAP == 0.60


def test_score_multipliers():
    assert SCORE_MULTIPLIERS == {5: 1.0, 4: 0.75, 3: 0.5, 2: 0.25, 1: 0.0, 0: 0.0}


def test_unit_limits_15k_sum():
    assert sum(UNIT_LIMITS["15k"].values()) == 663 + 477 + 352 + 1067


def test_proxy_only_for_guangfa():
    assert FUNDS["027521"].proxy_code == "025343"
    assert all(f.proxy_code is None for c, f in FUNDS.items() if c != "027521")


def test_cash_min_by_regime():
    assert REGIME_CASH_MIN == {
        "offensive": 0.15, "neutral": 0.25, "protect": 0.40, "defensive": 0.60,
    }
