"""SignalReport 组装：指标 → 评分 → 模式 → 目标权重 → 闸门 → 建议动作（PDF 16 章伪代码）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .config import (
    DEADBAND_AMOUNT, DEADBAND_BUY_TOTAL_PCT, DEADBAND_WEIGHT, FUNDS,
    MAX_UNITS_PER_WEEK, PROFIT_LOCK_12, PROFIT_LOCK_20, DD_HARD,
    REGIME_CASH_MIN, UNIT_LIMITS,
)
from .constraints import apply_caps
from .indicators import (
    drawdown_from_high, last_daily_return, ma, period_return, realized_vol,
)
from .regime import market_regime
from .rules import (
    detect_buy_signal, detect_sell_signal,
    gate_portfolio_ok, gate_position_ok, gate_score_ok,
)
from .scoring import score_multiplier, trend_score
from .sizing import target_weight as _target_weight, vol_multiplier as _vol_mult


@dataclass(frozen=True)
class Metrics:
    last: float
    ma20: float
    ma60: float
    r20: float
    r60: float
    vol20: float
    dd20: float
    day_ret: float


def compute_metrics(nav: pd.Series) -> Metrics:
    return Metrics(
        last=float(nav.iloc[-1]), ma20=ma(nav, 20), ma60=ma(nav, 60),
        r20=period_return(nav, 20), r60=period_return(nav, 60),
        vol20=realized_vol(nav, 20), dd20=drawdown_from_high(nav, 20),
        day_ret=last_daily_return(nav),
    )


@dataclass(frozen=True)
class AccountState:
    total_value: float
    cash_value: float
    peak_value: float
    net_contributed: float
    peak_profit_rate: float

    @property
    def portfolio_dd(self) -> float:
        return 1 - self.total_value / self.peak_value if self.peak_value > 0 else 0.0


@dataclass
class FundDecision:
    code: str
    name: str
    score: int
    score_multiplier: float
    vol20: float
    vol_multiplier: float
    regime_base_weight: float
    target_weight: float
    current_value: float
    target_value: float
    gap: float
    action: str          # 'BUY' | 'SELL' | 'HOLD'
    reason_code: str     # B1-B4 / S1-S4 / P1-P2 / N0
    amount: float
    units: float
    gates: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class SignalReport:
    as_of: str
    regime: str
    total_value: float
    portfolio_dd: float
    peak_profit_rate: float
    cash_value: float
    cash_weight: float
    decisions: list[FundDecision]
    weekly_unit_budget: int
    account_actions: list[str]


_BUY_PRIORITY = {"B2": 0, "B1": 1, "B4": 2, "B3": 3}


def build_decisions(
    regime: str,
    scores: dict[str, int],
    vols: dict[str, float],
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
) -> list[FundDecision]:
    total = account.total_value
    dd = account.portfolio_dd
    unit_limits = UNIT_LIMITS[capital_plan]
    prev_scores = prev_scores or {}

    raw_weights = {
        c: _target_weight(regime, c, scores[c], vols[c]) for c in FUNDS
    }
    weights = apply_caps(raw_weights, regime)

    cash_min_value = total * REGIME_CASH_MIN[regime]
    cash_available = max(0.0, account.cash_value - cash_min_value)

    decisions: list[FundDecision] = []
    for code, fund in FUNDS.items():
        nav = navs[code]
        score = scores[code]
        vol = vols[code]
        current = holdings[code]
        tw = weights[code]
        target_value = total * tw
        gap = target_value - current
        gates = {
            "portfolio": gate_portfolio_ok(dd, fund.bucket),
            "score": gate_score_ok(code, score),
            "position": gate_position_ok(code, nav),
            "cash": True,  # 资金闸门仅约束买入侧；卖出/不动恒为 True
        }
        d = FundDecision(
            code=code, name=fund.name, score=score,
            score_multiplier=score_multiplier(score), vol20=vol,
            vol_multiplier=_vol_mult(vol, fund.vol_bands),
            regime_base_weight=raw_weights[code], target_weight=tw,
            current_value=current, target_value=target_value, gap=gap,
            action="HOLD", reason_code="N0", amount=0.0, units=0.0, gates=gates,
        )

        in_deadband = abs(gap) < DEADBAND_AMOUNT or abs(gap) / total < DEADBAND_WEIGHT

        if gap < 0:
            # --- 卖出侧：硬信号（S1/S2/S3）与 S4 硬风控不受死区限制（PDF 9.1 硬风控不受限制） ---
            sell = detect_sell_signal(code, nav, score, prev_scores.get(code))
            if sell is not None:
                reason, frac = sell
                if frac == "to_core":
                    # PDF 算例 B：降至目标或核心仓，取更低者（更保守）
                    amount = max(0.0, current - total * min(fund.core_weight, tw))
                else:
                    amount = float(frac) * current
                    if reason == "S1":
                        amount = max(amount, current - target_value)
                d.action, d.reason_code = "SELL", reason
                d.amount = round(amount, 2)
            elif dd >= DD_HARD:
                # S4 硬风控纠偏：可直接卖到目标，不受 25% 缓冲与死区限制（PDF 9.1）
                d.action, d.reason_code = "SELL", "S4"
                d.amount = round(min(-gap, current), 2)
            elif not in_deadband:
                # 目标权重纠偏卖出（死区 300 元 / 3pp，PDF 9.1）：普通缓冲每周最多 25%
                d.action, d.reason_code = "SELL", "S1"
                d.amount = round(min(-gap, current * 0.25), 2)
                d.notes.append("普通纠偏受每周25%缓冲约束")
        elif gap > 0:
            # --- 买入侧（死区按 Buy 结果判定：<300 元或 <总资金 1.5%，PDF 8.3） ---
            gates["cash"] = cash_available > 0
            if all(gates.values()):
                signal = detect_buy_signal(code, nav, score, prev_scores.get(code))
                if signal is None and gap / total >= DEADBAND_WEIGHT and score >= 3:
                    signal = "B4"  # 再平衡买入
                if signal is not None:
                    factor = 0.5 if signal == "B3" else 1.0
                    amount = min(gap, unit_limits[code] * factor, cash_available)
                    if amount >= DEADBAND_AMOUNT and amount >= DEADBAND_BUY_TOTAL_PCT * total:
                        d.action, d.reason_code = "BUY", signal
                        d.amount = round(amount, 2)
                        d.units = factor
            elif not gates["cash"]:
                d.notes.append("现金不足，买入被资金闸门拦截")
            elif not gates["portfolio"]:
                d.notes.append("组合回撤闸门：禁止新增科技")
            elif not gates["score"]:
                d.notes.append(f"评分 {score} 未达买入门槛 {fund.min_score_to_buy}")
            elif not gates["position"]:
                d.notes.append("位置闸门：偏离 MA20 过高或单日涨幅>5%")
        decisions.append(d)

    # 周单元预算：按 B2>B1>B4>B3 分配（同优先级红利桶先于科技桶，PDF 07 章），超额者降级 HOLD
    budget = float(MAX_UNITS_PER_WEEK)
    for d in sorted((x for x in decisions if x.action == "BUY"),
                    key=lambda x: (
                        _BUY_PRIORITY[x.reason_code],
                        0 if FUNDS[x.code].bucket == "dividend" else 1,
                    )):
        if d.units <= budget:
            budget -= d.units
        else:
            d.action, d.reason_code, d.amount, d.units = "HOLD", "N0", 0.0, 0.0
            d.notes.append("超出本周单元预算，顺延")
    return decisions


def build_signal_report(
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
    as_of: date | None = None,
) -> SignalReport:
    scores = {c: trend_score(navs[c]) for c in FUNDS}
    vols = {c: realized_vol(navs[c], 20) for c in FUNDS}
    tech_scores = {c: scores[c] for c in FUNDS if FUNDS[c].bucket == "tech"}
    regime = market_regime(tech_scores, account.portfolio_dd, account.peak_profit_rate)
    decisions = build_decisions(
        regime, scores, vols, navs, holdings, account, capital_plan, prev_scores,
    )

    account_actions: list[str] = []
    if account.peak_profit_rate >= PROFIT_LOCK_20:
        account_actions.append("P2 峰值利润率≥20%：现金 ≥50%，等待新中期趋势")
    elif account.peak_profit_rate >= PROFIT_LOCK_12:
        lock = 0.5 * max(0.0, account.peak_value - account.net_contributed)
        account_actions.append(f"P2 峰值利润率≥12%：至少锁定 {lock:.0f} 元浮盈转现金，现金 ≥40%")
    if account.portfolio_dd >= DD_HARD:
        account_actions.append("S4 硬防御：现金 ≥70%，仅保留核心仓，重新评估风险承受能力")

    return SignalReport(
        as_of=(as_of or date.today()).isoformat(),
        regime=regime,
        total_value=account.total_value,
        portfolio_dd=account.portfolio_dd,
        peak_profit_rate=account.peak_profit_rate,
        cash_value=account.cash_value,
        cash_weight=account.cash_value / account.total_value if account.total_value else 0.0,
        decisions=decisions,
        weekly_unit_budget=MAX_UNITS_PER_WEEK,
        account_actions=account_actions,
    )
