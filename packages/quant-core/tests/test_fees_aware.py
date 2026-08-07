import pytest

from quant_core.fees import fee_aware_sell


def test_empty_lots_allows_sell():
    amount, fee, notes = fee_aware_sell([], 3000, 1.5, 0.005)
    assert amount == 3000
    assert fee == 0
    assert notes == []


def test_all_free_lots():
    lots = [
        {"shares": 1000, "holding_days": 365, "fee_rate": 0.0},
        {"shares": 500, "holding_days": 800, "fee_rate": 0.0},
    ]
    amount, fee, notes = fee_aware_sell(lots, 2250, 1.5, 0.005)
    assert amount == 2250
    assert fee == 0


def test_mixed_batches_weighted_average():
    lots = [
        {"shares": 1000, "holding_days": 7, "fee_rate": 0.015},
        {"shares": 1000, "holding_days": 365, "fee_rate": 0.005},
    ]
    amount, fee, notes = fee_aware_sell(lots, 3000, 1.5, 0.02)
    # 全部卖出 2000 份额 × 1.5 = 3000，加权费率 1%
    assert amount == 3000
    assert fee == pytest.approx(30.0, abs=0.01)
    assert any("1.00%" in n for n in notes)


def test_high_fee_truncation():
    lots = [
        {"shares": 500, "holding_days": 3, "fee_rate": 0.015},   # 高费率
        {"shares": 1000, "holding_days": 365, "fee_rate": 0.0},  # 免费
    ]
    amount, fee, notes = fee_aware_sell(lots, 2250, 1.5, 0.005)
    # 第一个高费率批次被跳过，只卖出免费部分
    assert amount == 1500.0
    assert fee == 0.0
    assert fee / amount <= 0.005 + 1e-9 if amount > 0 else True
    assert any("跳过" in n or "截断" in n for n in notes)


def test_zero_desired_amount():
    assert fee_aware_sell([], 0, 1.5, 0.005) == (0, 0, [])
