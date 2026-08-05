"""买入四闸门 + B/S 信号识别（PDF 06/08/09 章）。engine 负责金额与周单元预算。"""
from __future__ import annotations

import pandas as pd

from .config import DD_WARN, FUNDS
from .indicators import drawdown_from_high, last_daily_return, ma


# --- 闸门 ---

def gate_portfolio_ok(portfolio_dd: float, bucket: str) -> bool:
    """组合回撤 ≥6% 停止新增科技；≥8% 只允许补防御仓（对基金买入等价）。"""
    return bucket != "tech" or portfolio_dd < DD_WARN


def gate_score_ok(code: str, score: int) -> bool:
    return score >= FUNDS[code].min_score_to_buy


def gate_position_ok(code: str, nav: pd.Series) -> bool:
    """科技基金：偏离 MA20 ≤ +8% 且单日涨幅 ≤5%（防追高）。"""
    if FUNDS[code].bucket != "tech":
        return True
    dev = float(nav.iloc[-1]) / ma(nav, 20) - 1
    if dev > 0.08:
        return False
    return last_daily_return(nav) <= 0.05


# --- 买入信号（B4 由 engine 按权重差判定） ---

def detect_buy_signal(
    code: str, nav: pd.Series, score: int, prev_score: int | None,
) -> str | None:
    ma20, ma60 = ma(nav, 20), ma(nav, 60)
    last = float(nav.iloc[-1])
    dd20 = drawdown_from_high(nav, 20)
    # B2 回撤加仓（优先级最高）：MA20>MA60、nav>MA60、距20日高点回撤4%-8%、当日转正
    if ma20 > ma60 and last > ma60 and 0.04 <= dd20 <= 0.08 and last_daily_return(nav) > 0:
        return "B2"
    # B1 趋势建仓：连续两次周度评分≥4 且 nav>MA60
    if prev_score is not None and prev_score >= 4 and score >= 4 and last > ma60:
        return "B1"
    # B3 突破加仓：创20日新高、当日涨幅≥2%（突破日，稳态上行不触发）、评分≥4、偏离 MA20 ≤6%
    if (
        last >= float(nav.iloc[-20:].max()) * (1 - 1e-9)
        and last_daily_return(nav) >= 0.02
        and score >= 4
        and last / ma20 - 1 <= 0.06
    ):
        return "B3"
    return None


# --- 卖出信号 ---

# S3 回撤档位边界容忍（0.2pp）：峰值刚滑出回撤窗口时，量得回撤比"距真实高点"小约 1 日涨幅，
# PDF 档位为整数百分比的人类量级，判定按约值处理。
_DD_STEP_TOL = 0.002

def _ma_at(nav: pd.Series, window: int, offset: int) -> float:
    """offset 个交易日之前的 MA(window)。offset=0 即当前。"""
    end = len(nav) - offset
    return float(nav.iloc[end - window:end].mean())


def detect_sell_signal(
    code: str, nav: pd.Series, score: int, prev_score: int | None,
) -> tuple[str, float | str] | None:
    """返回 (理由, 卖出比例) 或 (理由, "to_core")。多个触发取最保守（卖出最多）。"""
    fund = FUNDS[code]
    last = float(nav.iloc[-1])
    ma20, ma60 = ma(nav, 20), ma(nav, 60)
    dd20 = drawdown_from_high(nav, 20)
    candidates: list[tuple[str, float | str]] = []

    if fund.bucket == "tech":
        if dd20 >= 0.18 - _DD_STEP_TOL:
            candidates.append(("S3", 1.0))                     # 退出全部战术仓
        elif dd20 >= 0.12 - _DD_STEP_TOL and last < ma60:
            candidates.append(("S3", 0.5))                     # 卖剩余战术仓 50%
        elif dd20 >= 0.08 - _DD_STEP_TOL and last < ma20:
            candidates.append(("S3", 0.25))
    else:
        if dd20 >= 0.10 - _DD_STEP_TOL and last < ma60:
            candidates.append(("S3", "to_core"))               # 摩根降至核心仓
        elif dd20 >= 0.06 - _DD_STEP_TOL and last < ma20:
            candidates.append(("S3", 0.20))

    # S2：低于 MA60 且 MA20 斜率为负 → 降至核心仓。
    # 斜率取截至昨日的 MA20 对比（单日急跌由 S3 阶梯处理，不视为趋势恶化）。
    if last < ma60 and _ma_at(nav, 20, 1) < _ma_at(nav, 20, 2):
        candidates.append(("S2", "to_core"))

    # S1：连续 2 日低于 MA20 且评分下降 ≥2 → 卖 25%（engine 再与"降至目标"取大）
    if (
        last < ma20
        and float(nav.iloc[-2]) < _ma_at(nav, 20, 1)
        and prev_score is not None
        and prev_score - score >= 2
    ):
        candidates.append(("S1", 0.25))

    if not candidates:
        return None

    def severity(item: tuple[str, float | str]) -> float:
        # "to_core" 是硬风控降仓（卖出至核心权重），优先于任何比例卖出
        return 2.0 if item[1] == "to_core" else float(item[1])

    return max(candidates, key=severity)
