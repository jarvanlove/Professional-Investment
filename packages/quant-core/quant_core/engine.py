"""SignalReport 组装：指标 → 评分 → 模式 → 目标权重 → 闸门 → 建议动作（PDF 16 章伪代码）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .config import (
    BUFFER_WEIGHT_DIFF, CONFIDENCE_FACTORS, DCA_HORIZON_DAYS,
    DEADBAND_AMOUNT, DEADBAND_BUY_TOTAL_PCT, DEADBAND_WEIGHT,
    DEFAULT_BASE_WEIGHTS, FEE_AVERSION_THRESHOLD, FUNDS,
    MAX_UNITS_PER_WEEK, MAX_WEEKLY_SELL_RATIO, PROFIT_LOCK_12,
    PROFIT_LOCK_20, DD_HARD, REGIME_CASH_MIN, UNIT_LIMITS,
)
from .confidence import compute_confidence
from .constraints import apply_caps
from .dca import DcaPlanCfg, dca_buy_offset, upcoming_dca
from .fees import fee_aware_sell
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


@dataclass
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
    confidence: float = 1.0
    confidence_level: str = "high"
    est_fee: float = 0.0
    net_amount: float = 0.0
    avg_fee_rate: float = 0.0
    is_dca: bool = False
    dca_upcoming: float = 0.0
    base_weight: float = 0.0


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
    weekly_plan: dict = field(default_factory=dict)


_BUY_PRIORITY = {"B2": 0, "B1": 1, "B4": 2, "B3": 3}


def _apply_base_floor(amount: float, current: float, total: float, base_weight: float) -> tuple[float, bool]:
    """返回（截断后的卖出金额，是否被底仓截断到 0）。"""
    floor_value = total * base_weight
    max_sell = max(0.0, current - floor_value)
    return min(amount, max_sell), max_sell <= 0


def _conf_factor(level: str, enabled: bool) -> float:
    if not enabled:
        return 1.0
    return CONFIDENCE_FACTORS.get(level, 1.0)


def build_decisions(
    regime: str,
    scores: dict[str, int],
    vols: dict[str, float],
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
    *,
    base_weights: dict[str, float] | None = None,
    max_sell_ratio: float = MAX_WEEKLY_SELL_RATIO,
    buffer_pp: float = BUFFER_WEIGHT_DIFF,
    dca_plans: tuple[DcaPlanCfg, ...] = (),
    lots_by_fund: dict[str, list[dict]] | None = None,
    confidence_scaling: bool = True,
    fee_aversion: float = FEE_AVERSION_THRESHOLD,
    proxy_used: dict[str, bool] | None = None,
    as_of: date | None = None,
) -> list[FundDecision]:
    total = account.total_value
    dd = account.portfolio_dd
    unit_limits = UNIT_LIMITS[capital_plan]
    prev_scores = prev_scores or {}
    base_weights = base_weights or DEFAULT_BASE_WEIGHTS
    lots_by_fund = lots_by_fund or {}
    proxy_used = proxy_used or {}
    as_of = as_of or date.today()

    raw_weights = {
        c: _target_weight(regime, c, scores[c], vols[c]) for c in FUNDS
    }
    weights = apply_caps(raw_weights, regime)

    cash_min_value = total * REGIME_CASH_MIN[regime]
    cash_available = max(0.0, account.cash_value - cash_min_value)

    upcoming = upcoming_dca(list(dca_plans), as_of, DCA_HORIZON_DAYS)
    total_upcoming_dca = sum(upcoming.values())
    discretionary_cash = max(0.0, cash_available - total_upcoming_dca)

    decisions: list[FundDecision] = []
    for code, fund in FUNDS.items():
        nav = navs[code]
        score = scores[code]
        vol = vols[code]
        current = holdings[code]
        tw = weights[code]
        target_value = total * tw
        gap = target_value - current
        base_weight = min(base_weights.get(code, 0.0), fund.cap)
        current_weight = current / total if total > 0 else 0.0
        in_buffer = abs(current_weight - tw) < buffer_pp
        in_deadband = abs(gap) < DEADBAND_AMOUNT or abs(gap) / total < DEADBAND_WEIGHT if total > 0 else abs(gap) < DEADBAND_AMOUNT

        confidence = compute_confidence(nav, used_proxy=proxy_used.get(code, False), score=score, as_of=as_of)
        conf_factor = _conf_factor(confidence.level, confidence_scaling)
        dca_upcoming = upcoming.get(code, 0.0)
        is_dca = dca_upcoming > 0

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
            confidence=confidence.score, confidence_level=confidence.level,
            est_fee=0.0, net_amount=0.0, avg_fee_rate=0.0,
            is_dca=is_dca, dca_upcoming=dca_upcoming, base_weight=base_weight,
        )
        if confidence.level != "high":
            d.notes.append(f"信号置信度 {confidence.level}（{confidence.score:.0%}）：{', '.join(confidence.factors)}")

        if gap < 0:
            # --- 硬卖出信号（S1/S2/S3 来自规则；S4 来自组合硬回撤）---
            hard_reason = None
            sell = detect_sell_signal(code, nav, score, prev_scores.get(code))
            if sell is not None:
                hard_reason, frac = sell
                if frac == "to_core":
                    amount = max(0.0, current - total * min(fund.core_weight, tw))
                else:
                    amount = float(frac) * current
                    if hard_reason == "S1":
                        amount = max(amount, current - target_value)
            elif dd >= DD_HARD:
                hard_reason = "S4"
                amount = min(-gap, current)
            else:
                amount = 0.0

            if hard_reason is not None:
                # 硬风控也要守底仓
                amount, floored = _apply_base_floor(amount, current, total, base_weight)
                if floored or amount <= 0:
                    d.action, d.reason_code = "HOLD", "N0"
                    d.notes.append("硬卖出被底仓保护截断")
                else:
                    # 赎回费感知（硬卖出同样计算，但不缩放置信度）
                    est, fee, fee_notes = fee_aware_sell(lots_by_fund.get(code, []), amount, nav.iloc[-1], fee_aversion)
                    if est <= 0:
                        d.notes.extend(fee_notes)
                        d.notes.append("高赎回费窗口阻止卖出")
                    else:
                        d.action, d.reason_code = "SELL", hard_reason
                        d.amount = round(est, 2)
                        d.est_fee = round(fee, 2)
                        d.net_amount = round(est - fee, 2)
                        d.avg_fee_rate = round(fee / est, 4) if est > 0 else 0.0
                        d.notes.extend(fee_notes)
            elif not in_deadband and not in_buffer:
                # 软卖出/再平衡：守底仓、最大单次比例、费用感知、置信度缩放
                desired = min(-gap, current * max_sell_ratio)
                desired, floored = _apply_base_floor(desired, current, total, base_weight)
                if floored or desired <= 0:
                    d.notes.append("目标卖出低于底仓，不卖出")
                else:
                    est, fee, fee_notes = fee_aware_sell(lots_by_fund.get(code, []), desired, nav.iloc[-1], fee_aversion)
                    if est > 0:
                        scaled = est * conf_factor
                        if scaled >= DEADBAND_AMOUNT:
                            d.action, d.reason_code = "SELL", "S1"
                            d.amount = round(scaled, 2)
                            d.est_fee = round(fee * (scaled / est) if est > 0 else 0.0, 2)
                            d.net_amount = round(d.amount - d.est_fee, 2)
                            d.avg_fee_rate = round(fee / est, 4) if est > 0 else 0.0
                            d.notes.extend(fee_notes)
                            if conf_factor < 1.0:
                                d.notes.append(f"低置信度下调卖出额至 {conf_factor:.0%}")
                            if max_sell_ratio != MAX_WEEKLY_SELL_RATIO:
                                d.notes.append(f"受单次最大卖出比例 {max_sell_ratio:.0%} 约束")
                        else:
                            d.notes.append("置信度缩放后低于交易死区")
                    else:
                        d.notes.extend(fee_notes)
                        d.notes.append("赎回费窗口阻止本次卖出")
            else:
                if in_buffer:
                    d.notes.append("当前权重在目标缓冲带内，不纠偏")
                else:
                    d.notes.append("差额在死区内，不交易")

        elif gap > 0:
            # --- 买入侧 ---
            gates["cash"] = discretionary_cash > 0
            if not gates["cash"]:
                d.notes.append("现金不足，买入被资金闸门拦截（已扣除未来定投预留）")
            if not gates["portfolio"]:
                d.notes.append("组合回撤闸门：禁止新增科技")
            if not gates["score"]:
                d.notes.append(f"评分 {score} 未达买入门槛 {fund.min_score_to_buy}")
            if not gates["position"]:
                d.notes.append("位置闸门：偏离 MA20 过高或单日涨幅>5%")

            if all(gates.values()):
                signal = detect_buy_signal(code, nav, score, prev_scores.get(code))
                if signal is None and gap / total >= DEADBAND_WEIGHT and score >= 3:
                    signal = "B4"  # 再平衡买入
                if signal is not None:
                    factor = 0.5 if signal == "B3" else 1.0
                    amount = min(gap, unit_limits[code] * factor, discretionary_cash)
                    # 抵扣未来定投
                    amount, dca_note = dca_buy_offset(code, amount, upcoming)
                    if dca_note:
                        d.notes.append(dca_note)
                    # 置信度缩放
                    amount = amount * conf_factor
                    if amount >= DEADBAND_AMOUNT and amount >= DEADBAND_BUY_TOTAL_PCT * total:
                        d.action, d.reason_code = "BUY", signal
                        d.amount = round(amount, 2)
                        d.units = factor
                        d.net_amount = d.amount
                        if conf_factor < 1.0:
                            d.notes.append(f"低置信度下调买入额至 {conf_factor:.0%}")
                    else:
                        d.notes.append("低于买入死区，转为观望")

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


def _build_weekly_plan(
    decisions: list[FundDecision],
    regime: str,
    account: AccountState,
    upcoming: dict[str, float],
    dca_plans: tuple[DcaPlanCfg, ...],
    as_of: date,
) -> dict:
    buys = [d for d in decisions if d.action == "BUY"]
    sells = [d for d in decisions if d.action == "SELL"]
    total_buy = sum(d.amount for d in buys)
    total_sell = sum(d.amount for d in sells)
    total_fee = sum(d.est_fee for d in sells)
    net_proceeds = total_sell - total_fee
    net_cash_change = net_proceeds - total_buy

    # 最近一期定投安排
    schedule: list[dict] = []
    for plan in dca_plans:
        if not plan.active or plan.amount <= 0:
            continue
        if plan.frequency == "weekly" and plan.day_of_week is not None:
            from datetime import timedelta
            from .dca import _next_weekday
            d = _next_weekday(as_of, plan.day_of_week)
            schedule.append({"fund_code": plan.fund_code, "date": d.isoformat(), "amount": plan.amount})
        elif plan.frequency == "monthly" and plan.day_of_month is not None:
            y, m = as_of.year, as_of.month
            try:
                d = date(y, m, plan.day_of_month)
            except ValueError:
                import calendar
                d = date(y, m, calendar.monthrange(y, m)[1])
            if d < as_of:
                m += 1
                if m > 12:
                    m, y = 1, y + 1
                try:
                    d = date(y, m, plan.day_of_month)
                except ValueError:
                    import calendar
                    d = date(y, m, calendar.monthrange(y, m)[1])
            schedule.append({"fund_code": plan.fund_code, "date": d.isoformat(), "amount": plan.amount})
    dca_total = sum(s["amount"] for s in schedule)

    cash_after = account.cash_value - total_buy - dca_total + net_proceeds
    min_cash = account.total_value * REGIME_CASH_MIN[regime]

    post_total = account.total_value + net_cash_change - dca_total
    post_weights: dict[str, float] = {}
    for d in decisions:
        post_value = d.current_value
        if d.action == "BUY":
            post_value += d.amount
        elif d.action == "SELL":
            post_value -= d.net_amount
        post_weights[d.code] = round(post_value / post_total, 4) if post_total > 0 else 0.0

    checklist = [
        "1. 确认本周净值已更新",
        "2. 按下方买入/卖出列表到场外平台下单",
        "3. 成交后返回「交易日志」补录",
        "4. 定投计划继续执行，不受信号影响",
    ]
    if cash_after < min_cash:
        checklist.insert(2, "⚠️ 预计现金低于模式下限，优先执行卖出或延迟非必要买入")
    if any(d.confidence_level == "low" for d in decisions):
        checklist.insert(2, "⚠️ 部分信号置信度低，建议复核后再下单")

    return {
        "planned_buys": [
            {
                "code": d.code, "name": d.name, "amount": d.amount,
                "reason_code": d.reason_code, "units": d.units,
                "confidence_level": d.confidence_level,
                "dca_upcoming": d.dca_upcoming,
            }
            for d in buys
        ],
        "planned_sells": [
            {
                "code": d.code, "name": d.name, "amount": d.amount,
                "reason_code": d.reason_code, "est_fee": d.est_fee,
                "net_amount": d.net_amount, "avg_fee_rate": d.avg_fee_rate,
                "confidence_level": d.confidence_level,
            }
            for d in sells
        ],
        "total_buy": round(total_buy, 2),
        "total_sell": round(total_sell, 2),
        "total_est_fee": round(total_fee, 2),
        "total_net_proceeds": round(net_proceeds, 2),
        "net_cash_change": round(net_cash_change, 2),
        "dca_schedule": schedule,
        "dca_total": round(dca_total, 2),
        "cash_after": round(cash_after, 2),
        "cash_after_ok": cash_after >= min_cash,
        "min_cash": round(min_cash, 2),
        "unit_budget_used": round(sum(d.units for d in buys), 1),
        "unit_budget_total": MAX_UNITS_PER_WEEK,
        "post_trade_weights": post_weights,
        "checklist": checklist,
    }


def build_signal_report(
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
    as_of: date | None = None,
    *,
    base_weights: dict[str, float] | None = None,
    max_sell_ratio: float = MAX_WEEKLY_SELL_RATIO,
    buffer_pp: float = BUFFER_WEIGHT_DIFF,
    dca_plans: tuple[DcaPlanCfg, ...] = (),
    lots_by_fund: dict[str, list[dict]] | None = None,
    confidence_scaling: bool = True,
    fee_aversion: float = FEE_AVERSION_THRESHOLD,
    proxy_used: dict[str, bool] | None = None,
) -> SignalReport:
    as_of = as_of or date.today()
    scores = {c: trend_score(navs[c]) for c in FUNDS}
    vols = {c: realized_vol(navs[c], 20) for c in FUNDS}
    tech_scores = {c: scores[c] for c in FUNDS if FUNDS[c].bucket == "tech"}
    regime = market_regime(tech_scores, account.portfolio_dd, account.peak_profit_rate)
    decisions = build_decisions(
        regime, scores, vols, navs, holdings, account, capital_plan, prev_scores,
        base_weights=base_weights,
        max_sell_ratio=max_sell_ratio,
        buffer_pp=buffer_pp,
        dca_plans=dca_plans,
        lots_by_fund=lots_by_fund,
        confidence_scaling=confidence_scaling,
        fee_aversion=fee_aversion,
        proxy_used=proxy_used,
        as_of=as_of,
    )

    account_actions: list[str] = []
    if account.peak_profit_rate >= PROFIT_LOCK_20:
        account_actions.append("P2 峰值利润率≥20%：现金 ≥50%，等待新中期趋势")
    elif account.peak_profit_rate >= PROFIT_LOCK_12:
        lock = 0.5 * max(0.0, account.peak_value - account.net_contributed)
        account_actions.append(f"P2 峰值利润率≥12%：至少锁定 {lock:.0f} 元浮盈转现金，现金 ≥40%")
    if account.portfolio_dd >= DD_HARD:
        account_actions.append("S4 硬防御：现金 ≥70%，仅保留核心仓，重新评估风险承受能力")

    upcoming = upcoming_dca(list(dca_plans), as_of, DCA_HORIZON_DAYS)
    weekly_plan = _build_weekly_plan(decisions, regime, account, upcoming, dca_plans, as_of)

    return SignalReport(
        as_of=as_of.isoformat(),
        regime=regime,
        total_value=account.total_value,
        portfolio_dd=account.portfolio_dd,
        peak_profit_rate=account.peak_profit_rate,
        cash_value=account.cash_value,
        cash_weight=account.cash_value / account.total_value if account.total_value else 0.0,
        decisions=decisions,
        weekly_unit_budget=MAX_UNITS_PER_WEEK,
        account_actions=account_actions,
        weekly_plan=weekly_plan,
    )
