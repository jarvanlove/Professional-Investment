# quant_core/fees.py
"""赎回费阶梯（PDF 03 章）与费用感知卖出截断。执行前仍须以销售平台实际持有天数为准。"""
from __future__ import annotations

from datetime import date

from .config import FUNDS


def redemption_fee_rate(code: str, days: int) -> float:
    for tier in FUNDS[code].fee_tiers:
        if tier.max_days is None or days < tier.max_days:
            return tier.rate
    return 0.0


def holding_days(buy_date: date, as_of: date) -> int:
    return (as_of - buy_date).days


def fee_aware_sell(
    lots: list[dict],
    desired_amount: float,
    nav: float,
    max_avg_fee_rate: float,
) -> tuple[float, float, list[str]]:
    """按 FIFO 逐批累计卖出金额，若加权平均费率超过阈值则截断。

    Parameters
    ----------
    lots: 批次列表，每项至少含 shares（剩余份额）和 holding_days。
    desired_amount: 希望卖出的金额。
    nav: 当前净值。
    max_avg_fee_rate: 可接受的加权平均赎回费率上限。

    Returns
    -------
    (amount, fee, notes)
    """
    notes: list[str] = []
    if nav <= 0 or desired_amount <= 0:
        return 0.0, 0.0, notes
    if not lots:
        # 无持仓批次时按免费处理（单元测试 / 无赎回费场景）
        return desired_amount, 0.0, notes

    remaining_value = desired_amount
    total_shares_sold = 0.0
    weighted_fee = 0.0
    selected_lots: list[tuple[float, float]] = []  # (shares, fee_rate)

    for lot in lots:
        shares_available = float(lot.get("shares", 0.0))
        if shares_available <= 1e-9:
            continue
        days = int(lot.get("holding_days", 0))
        rate = lot.get("fee_rate")
        if rate is None:
            rate = redemption_fee_rate(lot.get("fund_code", ""), days)
        rate = float(rate)
        # 单批次费率已高于阈值则跳过（宁可不卖这部分）
        if rate > max_avg_fee_rate:
            notes.append(f"跳过 {days} 天高费率批次({rate*100:.2f}%)")
            continue
        # 该批次最多可卖出金额
        lot_value = shares_available * nav
        take_value = min(lot_value, remaining_value)
        take_shares = take_value / nav

        # 试探加入后的加权费率
        new_weighted_fee = weighted_fee + take_shares * rate
        new_total_shares = total_shares_sold + take_shares
        avg = new_weighted_fee / new_total_shares if new_total_shares > 0 else 0.0

        if avg > max_avg_fee_rate and selected_lots:
            # 加入该批次会突破阈值，截断到此为止
            notes.append(f"高赎回费批次({days}天/{rate*100:.2f}%)截断卖出")
            break

        selected_lots.append((take_shares, rate))
        total_shares_sold = new_total_shares
        weighted_fee = new_weighted_fee
        remaining_value -= take_value
        if remaining_value <= 1e-9:
            break

    if total_shares_sold <= 1e-9:
        return 0.0, 0.0, notes

    amount = total_shares_sold * nav
    avg_rate = weighted_fee / total_shares_sold
    fee = amount * avg_rate
    if avg_rate > max_avg_fee_rate:
        notes.append(f"加权赎回费率 {avg_rate*100:.2f}% 高于阈值 {max_avg_fee_rate*100:.2f}%")
    else:
        notes.append(f"加权赎回费率 {avg_rate*100:.2f}%")
    return amount, fee, notes
