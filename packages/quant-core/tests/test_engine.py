import numpy as np
import pandas as pd
import pytest

from quant_core.engine import (
    AccountState, build_decisions, build_signal_report, compute_metrics,
)


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    return pd.Series(vals, index=pd.date_range("2026-01-01", periods=days, freq="B"))


def make_account(total=19044.07, cash=15000.0):
    return AccountState(
        total_value=total, cash_value=cash, peak_value=total,
        net_contributed=total, peak_profit_rate=0.0,
    )


def test_compute_metrics_keys():
    m = compute_metrics(uptrend())
    assert m.ma20 > 0 and m.ma60 > 0 and m.vol20 >= 0
    assert m.last == pytest.approx(float(uptrend().iloc[-1]))


def test_build_decisions_example_a():
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {"001480": 0.20, "025343": 0.20, "027521": 0.20, "005052": 0.10}
    navs = {c: uptrend() for c in scores}
    # 财通/摩根：上行后小幅回落一天，不在 20 日新高 → 不触 B3，gap≥3pp 走 B4
    dip = uptrend().tolist()
    dipped = pd.Series(dip + [dip[-1] * 0.995],
                       index=pd.date_range("2026-01-01", periods=81, freq="B"))
    navs["001480"] = dipped
    navs["005052"] = dipped
    # 长盛：B2 回撤形态（MA20>MA60、nav>MA60、距 20 日高点回撤 4-8%、当日转正）
    vals = (100 * 1.002 ** np.arange(75)).tolist()
    peak = vals[-1] * 1.01
    vals += [peak, peak * 0.97, peak * 0.955, peak * 0.945, peak * 0.955]
    navs["025343"] = pd.Series(vals, index=pd.date_range("2026-01-01", periods=80, freq="B"))
    holdings = {"001480": 2107.85, "025343": 949.85, "027521": 495.12, "005052": 491.25}
    decisions = build_decisions(
        "neutral", scores, vols, navs, holdings, make_account(), capital_plan="15k",
        confidence_scaling=False,
    )
    by_code = {d.code: d for d in decisions}
    # 目标权重与目标金额（PDF 算例 A 表格）
    assert by_code["001480"].target_weight == pytest.approx(0.1875)
    assert by_code["025343"].target_weight == pytest.approx(0.075)
    assert by_code["027521"].target_weight == pytest.approx(0.025)
    assert by_code["005052"].target_weight == pytest.approx(0.1875)
    assert by_code["001480"].target_value == pytest.approx(3571, abs=1)
    assert by_code["025343"].target_value == pytest.approx(1428, abs=1)
    assert by_code["027521"].target_value == pytest.approx(476, abs=1)
    assert by_code["005052"].target_value == pytest.approx(3571, abs=1)
    # 周单元预算 2：B2 长盛 + B4 摩根（红利桶优先）执行；财通 B4 顺延
    assert by_code["025343"].action == "BUY" and by_code["025343"].reason_code == "B2"
    assert by_code["025343"].amount == pytest.approx(477.0)
    assert by_code["005052"].action == "BUY" and by_code["005052"].reason_code == "B4"
    assert by_code["005052"].amount == pytest.approx(1067.0)
    assert by_code["001480"].action == "HOLD"
    assert any("超出本周单元预算" in n for n in by_code["001480"].notes)
    assert by_code["027521"].action == "HOLD"                 # gap=-19 死区
    buys = [d for d in decisions if d.action == "BUY"]
    assert sum(d.units for d in buys) <= 2                    # 周单元预算
    assert sum(d.amount for d in buys) == pytest.approx(477.0 + 1067.0)


def test_sell_to_core_bypasses_weekly_buffer():
    scores = {"001480": 2, "025343": 4, "027521": 4, "005052": 4}
    vols = {c: 0.20 for c in scores}
    # 财通缓慢阴跌：每日 -0.3%（80 点），dd20≈5.5%（<8% 不触 S3），
    # nav<MA60 且 MA20 斜率为负（只触 S2）
    decline = 100 * 0.997 ** np.arange(80)
    navs = {c: uptrend() for c in scores}
    navs["001480"] = pd.Series(decline,
                               index=pd.date_range("2026-01-01", periods=80, freq="B"))
    holdings = {"001480": 6000.0, "025343": 3000.0, "027521": 1000.0, "005052": 5000.0}
    account = AccountState(total_value=24000.0, cash_value=9000.0, peak_value=24000.0,
                           net_contributed=24000.0, peak_profit_rate=0.0)
    decisions = build_decisions("neutral", scores, vols, navs, holdings, account,
                                confidence_scaling=False)
    ct = {d.code: d for d in decisions}["001480"]
    assert ct.action == "SELL"
    # 默认底仓 8%（1920 元），硬风控卖到目标/核心仓取低者后受底仓保护：6000-1920=4080
    assert ct.amount == pytest.approx(4080.0)
    assert ct.reason_code == "S2"


def test_s4_correction_sell_bypasses_weekly_buffer():
    """PDF 9.1：组合回撤达硬阈值的纠偏卖出不受 25% 周缓冲限制。"""
    codes = ("001480", "025343", "027521", "005052")
    scores = {c: 5 for c in codes}
    vols = {c: 0.10 for c in codes}
    navs = {c: uptrend() for c in codes}  # 上行净值：无 S1/S2/S3 硬信号
    total = 10000.0
    peak = total / 0.85  # 组合回撤 = 15% = DD_HARD
    holdings = {"001480": 0.0, "025343": 0.0, "027521": 0.0, "005052": 5000.0}
    account = AccountState(total_value=total, cash_value=5000.0, peak_value=peak,
                           net_contributed=total, peak_profit_rate=0.0)
    decisions = build_decisions("defensive", scores, vols, navs, holdings, account)
    d = {x.code: x for x in decisions}["005052"]
    assert d.action == "SELL" and d.reason_code == "S4"
    # 目标 25%×10000=2500 → 卖 2500；若受 25% 周缓冲仅 1250
    assert d.amount == pytest.approx(2500.0)
    assert not any("25%" in n for n in d.notes)


def test_cash_gate_blocks_buy_with_note():
    """PDF 8.1 第四道闸门：可用现金为 0 时买入被资金闸门拦截并给出说明。"""
    codes = ("001480", "025343", "027521", "005052")
    scores = {c: 4 for c in codes}
    vols = {c: 0.20 for c in codes}
    navs = {c: uptrend() for c in codes}
    total = 20000.0
    holdings = {"001480": 1000.0, "025343": 3000.0, "027521": 2000.0, "005052": 4000.0}
    account = AccountState(total_value=total, cash_value=0.0, peak_value=total,
                           net_contributed=total, peak_profit_rate=0.0)
    decisions = build_decisions("neutral", scores, vols, navs, holdings, account)
    by_code = {d.code: d for d in decisions}
    ct = by_code["001480"]  # gap>0 且其余三道闸门均通过
    assert ct.gates["portfolio"] and ct.gates["score"] and ct.gates["position"]
    assert ct.gates["cash"] is False
    assert ct.action == "HOLD"
    assert any("资金闸门" in n for n in ct.notes)
    # 卖出侧决策的资金闸门恒为 True（不显示伪 ❌）
    assert by_code["005052"].gap > 0 or by_code["005052"].gates["cash"] is True


def test_build_signal_report_end_to_end():
    navs = {c: uptrend() for c in ("001480", "025343", "027521", "005052")}
    holdings = {"001480": 2107.85, "025343": 949.85, "027521": 495.12, "005052": 491.25}
    report = build_signal_report(navs, holdings, make_account())
    assert report.regime in ("offensive", "neutral", "protect", "defensive")
    assert len(report.decisions) == 4
    assert report.cash_weight == pytest.approx(15000.0 / 19044.07)


def test_profit_lock_account_action():
    account = AccountState(total_value=22400.0, cash_value=5000.0, peak_value=22400.0,
                           net_contributed=20000.0, peak_profit_rate=0.12)
    navs = {c: uptrend() for c in ("001480", "025343", "027521", "005052")}
    holdings = {"001480": 5000.0, "025343": 3000.0, "027521": 1500.0, "005052": 7900.0}
    report = build_signal_report(navs, holdings, account)
    assert any("P2" in a for a in report.account_actions)
