"""定投计划现金流整合：未来 N 天内的定投金额，以及买入抵扣逻辑。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class DcaPlanCfg:
    fund_code: str
    frequency: str  # weekly | monthly
    amount: float
    day_of_week: int | None = None   # 0=周一 .. 4=周五
    day_of_month: int | None = None  # 1-28
    active: bool = True


def _next_weekday(start: date, weekday: int) -> date:
    """返回 start 之后（含）第一个 weekday（周一=0）。"""
    days = (weekday - start.weekday()) % 7
    return start + timedelta(days=days)


def _occurrences_in_horizon(
    plan: DcaPlanCfg,
    start: date,
    horizon_days: int,
) -> int:
    """计算从 start（含）起 horizon_days 内预计触发几次定投。"""
    if not plan.active or plan.amount <= 0:
        return 0
    end = start + timedelta(days=horizon_days)
    if plan.frequency == "weekly" and plan.day_of_week is not None:
        d = _next_weekday(start, plan.day_of_week)
        count = 0
        while d <= end:
            count += 1
            d += timedelta(days=7)
        return count
    if plan.frequency == "monthly" and plan.day_of_month is not None:
        # 从当前月份开始
        y, m = start.year, start.month
        count = 0
        while True:
            try:
                d = date(y, m, plan.day_of_month)
            except ValueError:
                # 29/30/31 被 schema 限制为 1-28，防御性回退
                import calendar
                d = date(y, m, calendar.monthrange(y, m)[1])
            if d > end:
                break
            if d >= start:
                count += 1
            m += 1
            if m > 12:
                m = 1
                y += 1
        return count
    return 0


def upcoming_dca(
    plans: list[DcaPlanCfg],
    as_of: date | None = None,
    horizon_days: int = 14,
) -> dict[str, float]:
    as_of = as_of or date.today()
    out: dict[str, float] = {}
    for plan in plans:
        n = _occurrences_in_horizon(plan, as_of, horizon_days)
        if n:
            out[plan.fund_code] = out.get(plan.fund_code, 0.0) + n * plan.amount
    return out


def dca_buy_offset(
    fund_code: str,
    planned_signal_amount: float,
    upcoming: dict[str, float],
) -> tuple[float, str | None]:
    """用即将发生的定投抵扣信号买入金额，避免同周重复买入。

    Returns
    -------
    (adjusted_amount, note)
    """
    dca = upcoming.get(fund_code, 0.0)
    if dca <= 0 or planned_signal_amount <= 0:
        return planned_signal_amount, None
    adjusted = max(0.0, planned_signal_amount - dca)
    note = f"未来 {dca:.0f} 元定投已抵扣信号买入"
    return adjusted, note
