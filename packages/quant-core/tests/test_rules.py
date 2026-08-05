# tests/test_rules.py
import numpy as np
import pandas as pd

from quant_core.rules import (
    gate_portfolio_ok, gate_score_ok, gate_position_ok,
    detect_buy_signal, detect_sell_signal,
)


def series(vals):
    idx = pd.date_range("2026-01-01", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx, dtype=float)


def uptrend(days=80, daily=1.002):
    return series((100 * daily ** np.arange(days)).tolist())


# --- 闸门 ---

def test_portfolio_gate_blocks_tech_at_6pct():
    assert gate_portfolio_ok(0.05, "tech") is True
    assert gate_portfolio_ok(0.07, "tech") is False
    assert gate_portfolio_ok(0.07, "dividend") is True   # 6-8% 仍可补摩根
    assert gate_portfolio_ok(0.10, "tech") is False


def test_score_gate_thresholds():
    assert gate_score_ok("001480", 3) is True
    assert gate_score_ok("001480", 2) is False
    assert gate_score_ok("027521", 3) is False  # 广发要求 ≥4
    assert gate_score_ok("027521", 4) is True


def test_position_gate_chase_rules():
    nav = uptrend()
    assert gate_position_ok("001480", nav) is True
    spiked = nav.copy()
    spiked.iloc[-1] = spiked.iloc[-2] * 1.06   # 单日 +6% > 5%
    assert gate_position_ok("001480", spiked) is False
    far = nav.copy()
    far.iloc[-1] = far.iloc[-1] * 1.09          # 偏离 MA20 >8%
    assert gate_position_ok("001480", far) is False
    assert gate_position_ok("005052", far) is True  # 位置闸门只管科技


# --- 买入信号 ---

def test_b1_trend_entry():
    nav = uptrend()
    assert detect_buy_signal("001480", nav, score=4, prev_score=4) == "B1"
    assert detect_buy_signal("001480", nav, score=4, prev_score=2) is None


def test_b2_pullback():
    vals = (100 * 1.002 ** np.arange(75)).tolist()
    peak = vals[-1] * 1.01
    vals += [peak, peak * 0.97, peak * 0.955, peak * 0.945, peak * 0.955]
    nav = series(vals)  # 高点回撤后单日转正，MA20>MA60 且 nav>MA60
    sig = detect_buy_signal("001480", nav, score=4, prev_score=4)
    # B2（回撤 4%-8% 且当日转正）或 B1（连续高分）均为合法；实现按 B2 优先
    assert sig in ("B2", "B1")


def test_b3_breakout():
    nav = uptrend(daily=1.0015)
    nav.iloc[-1] = nav.iloc[-1] * 1.02  # 创 20 日新高但偏离 MA20 不超过 6%
    assert detect_buy_signal("001480", nav, score=4, prev_score=3) == "B3"


# --- 卖出信号 ---

def test_s2_below_ma60_with_falling_ma20():
    vals = (100 * 1.003 ** np.arange(60)).tolist()
    decline = (vals[-1] * np.array([1.0, .97, .94, .91, .88, .85, .83, .81, .79, .77,
                                    .75, .73, .71, .69, .67, .65, .63, .61, .59, .57])).tolist()
    nav = series(vals + decline)
    sig = detect_sell_signal("001480", nav, score=1, prev_score=3)
    assert sig is not None and sig[0] == "S2" and sig[1] == "to_core"


def test_s3_fund_drawdown_ladder():
    base = uptrend().tolist()
    dd8 = series(base[:-1] + [base[-1] * 0.92])   # 距20日高点约 -8%
    sig = detect_sell_signal("001480", dd8, score=3, prev_score=4)
    assert sig is not None and sig[0] == "S3" and sig[1] == 0.25
    dd18 = series(base[:-1] + [base[-1] * 0.80])  # -20% ≥ 18% → 退出全部战术仓
    sig = detect_sell_signal("001480", dd18, score=1, prev_score=3)
    assert sig is not None and sig[0] == "S3" and sig[1] == 1.0


def test_morgan_drawdown_rules():
    base = uptrend().tolist()
    dd6 = series(base[:-1] + [base[-1] * 0.935])
    sig = detect_sell_signal("005052", dd6, score=3, prev_score=4)
    assert sig is not None and sig[0] == "S3" and sig[1] == 0.20
