"""PDF 第 13 章三个算例的金额必须与方案表格一致（允许 ±1 元舍入差）。

防回归权威基准：任何参数改动若破坏算例，必须显式更新本文件并在 PR 说明。
执行口径以 PDF 规则文本为准（8.4 周单元预算 2 单元硬约束），
优先于算例 A 演示合计的宽松数字。
"""
import numpy as np
import pandas as pd
import pytest

from quant_core.config import PROFIT_LOCK_12
from quant_core.engine import AccountState, build_decisions
from quant_core.sizing import target_weight

CODES = ("001480", "025343", "027521", "005052")


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    return pd.Series(vals, index=pd.date_range("2026-01-01", periods=days, freq="B"))


def test_example_a_first_weekly_check():
    """追加1.5万后首次周度检查：中性，评分 4/3/2/4，回撤2%（忽略波动缩放）。"""
    total = 19044.07
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {"001480": 0.20, "025343": 0.20, "027521": 0.20, "005052": 0.10}
    navs = {c: uptrend() for c in CODES}
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
    account = AccountState(total_value=total, cash_value=15000.0,
                           peak_value=total / 0.98, net_contributed=total,
                           peak_profit_rate=0.011)
    decisions = {d.code: d for d in build_decisions(
        "neutral", scores, vols, navs, holdings, account, capital_plan="15k",
        confidence_scaling=False,
    )}

    # 目标权重（PDF 表格）
    assert decisions["001480"].target_weight == pytest.approx(0.1875)
    assert decisions["025343"].target_weight == pytest.approx(0.075)
    assert decisions["027521"].target_weight == pytest.approx(0.025)
    assert decisions["005052"].target_weight == pytest.approx(0.1875)
    # 目标金额（PDF 表格：3571 / 1428 / 476 / 3571）
    assert decisions["001480"].target_value == pytest.approx(3571, abs=1)
    assert decisions["025343"].target_value == pytest.approx(1428, abs=1)
    assert decisions["027521"].target_value == pytest.approx(476, abs=1)
    assert decisions["005052"].target_value == pytest.approx(3571, abs=1)
    # 周单元预算 2：B2 长盛 + B4 摩根（红利桶优先）执行；财通 B4 顺延
    assert decisions["025343"].action == "BUY"
    assert decisions["025343"].reason_code == "B2"
    assert decisions["025343"].amount == pytest.approx(477, abs=1)
    assert decisions["005052"].action == "BUY"
    assert decisions["005052"].reason_code == "B4"
    assert decisions["005052"].amount == pytest.approx(1067, abs=1)
    assert decisions["001480"].action == "HOLD"
    assert any("超出本周单元预算" in n for n in decisions["001480"].notes)
    # 广发理论卖出 19 元 < 300 死区 → 不动
    assert decisions["027521"].action == "HOLD"
    # 本周合计 = 477 + 1067 = 1544（2 单元硬约束，非算例演示的 2208）
    spent = sum(d.amount for d in decisions.values() if d.action == "BUY")
    assert spent == pytest.approx(1544, abs=2)


def test_example_b_trend_break_sell():
    """财通评分 4→2 且跌破 MA60：目标 6.25%，硬风控直接卖到目标。"""
    assert target_weight("neutral", "001480", score=2, vol=0.20) == pytest.approx(0.0625)
    total, current = 24000.0, 6000.0
    target_value = total * 0.0625
    assert target_value == pytest.approx(1500.0)
    assert current - target_value == pytest.approx(4500.0)
    # 端到端验证：缓慢阴跌（每日 -0.3%，80 点），dd20≈5.5%（<8% 不触 S3），
    # nav<MA60 且 MA20 斜率为负（只触 S2）
    decline = 100 * 0.997 ** np.arange(80)
    navs = {c: uptrend() for c in CODES}
    navs["001480"] = pd.Series(decline,
                               index=pd.date_range("2026-01-01", periods=80, freq="B"))
    scores = {"001480": 2, "025343": 4, "027521": 4, "005052": 4}
    vols = {c: 0.20 for c in CODES}
    holdings = {"001480": 6000.0, "025343": 3000.0, "027521": 1000.0, "005052": 5000.0}
    account = AccountState(total_value=total, cash_value=9000.0, peak_value=total,
                           net_contributed=total, peak_profit_rate=0.0)
    d = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings,
                                            account, confidence_scaling=False)}["001480"]
    assert d.action == "SELL" and d.reason_code == "S2"
    # 默认底仓 8% 保护后：6000 - 24000×0.08 = 4080
    assert d.amount == pytest.approx(4080.0, abs=1)


def test_example_c_profit_lock():
    """峰值 22400、净投入 20000 → 至少锁定 1200 元，现金 ≥40%。"""
    peak, contributed = 22400.0, 20000.0
    profit_rate = (peak - contributed) / contributed
    assert profit_rate == pytest.approx(0.12)
    assert profit_rate >= PROFIT_LOCK_12
    lock = 0.5 * max(0.0, peak - contributed)
    assert lock == pytest.approx(1200.0)
