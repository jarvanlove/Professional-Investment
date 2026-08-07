from datetime import date

import pytest

from quant_core.dca import DcaPlanCfg, dca_buy_offset, upcoming_dca


def test_upcoming_weekly():
    plans = [
        DcaPlanCfg(fund_code="001480", frequency="weekly", amount=1000, day_of_week=4),
    ]
    # 2026-08-10 是周一（weekday=0），未来 14 天内包含 8/14、8/21 两个周五
    assert upcoming_dca(plans, date(2026, 8, 10), 14)["001480"] == 2000


def test_upcoming_weekly_counts_multiple():
    plans = [DcaPlanCfg(fund_code="001480", frequency="weekly", amount=500, day_of_week=1)]
    # 2026-08-07 是周五，未来 14 天内包含 8/10、8/17 两个周一
    assert upcoming_dca(plans, date(2026, 8, 7), 14)["001480"] == 1000


def test_upcoming_monthly():
    plans = [DcaPlanCfg(fund_code="025343", frequency="monthly", amount=2000, day_of_month=15)]
    # 8/7 -> 8/15 一次
    assert upcoming_dca(plans, date(2026, 8, 7), 14)["025343"] == 2000
    # 8/16 -> 9/15 不在 14 天内
    assert "025343" not in upcoming_dca(plans, date(2026, 8, 16), 14)


def test_inactive_plan_excluded():
    plans = [DcaPlanCfg(fund_code="001480", frequency="weekly", amount=1000, day_of_week=4, active=False)]
    assert upcoming_dca(plans, date(2026, 8, 7), 14) == {}


def test_buy_offset_reduces_signal_amount():
    upcoming = {"001480": 600}
    amount, note = dca_buy_offset("001480", 1000, upcoming)
    assert amount == 400
    assert note and "抵扣" in note


def test_buy_offset_zero_when_dca_covers_all():
    upcoming = {"001480": 1000}
    amount, note = dca_buy_offset("001480", 800, upcoming)
    assert amount == 0
    assert note and "抵扣" in note


def test_buy_offset_no_dca():
    assert dca_buy_offset("001480", 500, {}) == (500, None)
