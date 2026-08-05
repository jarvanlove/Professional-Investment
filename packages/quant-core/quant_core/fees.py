# quant_core/fees.py
"""赎回费阶梯（PDF 03 章）。执行前仍须以销售平台实际持有天数为准。"""
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
