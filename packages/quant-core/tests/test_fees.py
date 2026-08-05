# tests/test_fees.py
from datetime import date

from quant_core.fees import redemption_fee_rate, holding_days


def test_caitong_fee_ladder():
    assert redemption_fee_rate("001480", 3) == 0.015
    assert redemption_fee_rate("001480", 10) == 0.0075
    assert redemption_fee_rate("001480", 100) == 0.005
    assert redemption_fee_rate("001480", 400) == 0.0025
    assert redemption_fee_rate("001480", 800) == 0.0


def test_c_share_fee_free_after_7_days():
    assert redemption_fee_rate("025343", 5) == 0.015
    assert redemption_fee_rate("025343", 7) == 0.0
    assert redemption_fee_rate("027521", 6) == 0.015
    assert redemption_fee_rate("027521", 8) == 0.0


def test_morgan_fee_ladder():
    assert redemption_fee_rate("005052", 3) == 0.015
    assert redemption_fee_rate("005052", 15) == 0.005
    assert redemption_fee_rate("005052", 30) == 0.0


def test_holding_days():
    assert holding_days(date(2026, 7, 1), date(2026, 8, 5)) == 35
