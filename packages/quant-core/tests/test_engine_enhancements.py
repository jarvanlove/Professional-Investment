from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant_core.config import DEFAULT_BASE_WEIGHTS
from quant_core.dca import DcaPlanCfg
from quant_core.engine import AccountState, build_decisions, build_signal_report

CODES = ("001480", "025343", "027521", "005052")


def uptrend(end: date, days: int = 120, daily: float = 1.002) -> pd.Series:
    vals = 100 * daily ** np.arange(days)
    idx = pd.date_range(end=end, periods=days, freq="D")
    return pd.Series(vals, index=idx)


def make_navs(as_of: date, days: int = 120, **overrides):
    end = as_of - pd.Timedelta(days=1)
    navs = {c: uptrend(end, days=days) for c in CODES}
    navs.update(overrides)
    return navs


AS_OF = date(2026, 8, 7)


def test_base_floor_blocks_sell_below_floor():
    scores = {c: 2 for c in CODES}
    vols = {c: 0.20 for c in CODES}
    end = AS_OF - pd.Timedelta(days=1)
    decline = 100 * 0.997 ** np.arange(120)
    navs = make_navs(AS_OF, **{"001480": pd.Series(decline, index=pd.date_range(end=end, periods=120, freq="D"))})
    holdings = {"001480": 6000.0, "025343": 3000.0, "027521": 1000.0, "005052": 5000.0}
    account = AccountState(total_value=24000.0, cash_value=9000.0, peak_value=24000.0,
                           net_contributed=24000.0, peak_profit_rate=0.0)
    d = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                            as_of=AS_OF, confidence_scaling=False)}["001480"]
    assert d.action == "SELL"
    floor_value = 24000 * DEFAULT_BASE_WEIGHTS["001480"]
    assert d.amount == pytest.approx(6000 - floor_value, abs=1)


def test_custom_max_sell_ratio():
    scores = {c: 5 for c in CODES}
    vols = {c: 0.10 for c in CODES}
    navs = make_navs(AS_OF)
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 8000.0}
    account = AccountState(total_value=20000.0, cash_value=10000.0, peak_value=20000.0,
                           net_contributed=20000.0, peak_profit_rate=0.0)
    d = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                            as_of=AS_OF, max_sell_ratio=0.10,
                                            confidence_scaling=False)}["005052"]
    assert d.action == "SELL"
    assert d.amount == pytest.approx(800, abs=1)  # 10% of 8000


def test_buffer_pp_holds_when_within_band():
    scores = {c: 5 for c in CODES}
    vols = {c: 0.10 for c in CODES}
    navs = make_navs(AS_OF)
    total = 20000.0
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 5050.0}
    account = AccountState(total_value=total, cash_value=15000.0, peak_value=total,
                           net_contributed=total, peak_profit_rate=0.0)
    d = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                            as_of=AS_OF, buffer_pp=0.02,
                                            confidence_scaling=False)}["005052"]
    assert d.action == "HOLD"
    assert any("缓冲带" in n for n in d.notes)


def test_confidence_scaling_reduces_buy():
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {c: 0.10 for c in CODES}
    # 用较短历史让置信度为 medium（0.7），005052 单元上限较大，缩放后仍高于死区
    navs = make_navs(AS_OF, days=70)
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 0.0}
    account = AccountState(total_value=20000.0, cash_value=15000.0, peak_value=20000.0,
                           net_contributed=20000.0, peak_profit_rate=0.0)
    off = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                              as_of=AS_OF, confidence_scaling=False)}["005052"]
    on = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                             as_of=AS_OF, confidence_scaling=True)}["005052"]
    assert off.action == "BUY"
    assert on.action == "BUY"
    assert on.amount < off.amount


def test_dca_offset_reduces_buy():
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {c: 0.10 for c in CODES}
    navs = make_navs(AS_OF, days=70)
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 0.0}
    account = AccountState(total_value=20000.0, cash_value=15000.0, peak_value=20000.0,
                           net_contributed=20000.0, peak_profit_rate=0.0)
    no_dca = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                                 as_of=AS_OF, confidence_scaling=False)}["005052"]
    # 月定投 8/8 一次，未来 14 天内仅 200 元
    plans = (DcaPlanCfg(fund_code="005052", frequency="monthly", amount=200, day_of_month=8),)
    with_dca = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings, account,
                                                   as_of=AS_OF, dca_plans=plans, confidence_scaling=False)}["005052"]
    assert with_dca.action == "BUY"
    assert with_dca.amount == pytest.approx(no_dca.amount - 200, abs=1)
    assert with_dca.dca_upcoming == 200


def test_weekly_plan_present():
    navs = make_navs(AS_OF)
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 0.0}
    account = AccountState(total_value=20000.0, cash_value=15000.0, peak_value=20000.0,
                           net_contributed=20000.0, peak_profit_rate=0.0)
    report = build_signal_report(navs, holdings, account, as_of=AS_OF, confidence_scaling=False)
    assert "weekly_plan" in report.__dict__
    assert report.weekly_plan["unit_budget_total"] == 2
    assert isinstance(report.weekly_plan["checklist"], list)
