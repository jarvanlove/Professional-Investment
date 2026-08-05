# quant_core/regime.py
"""市场模式判定（PDF 05 章）。优先级：defensive > protect > offensive > neutral。"""
from __future__ import annotations

from .config import (
    DD_DEFENSIVE, DD_WARN, PROFIT_PROTECT_TRIGGER, PROFIT_PULLBACK_TRIGGER,
)


def market_regime(
    tech_scores: dict[str, int],
    portfolio_dd: float,
    peak_profit_rate: float,
) -> str:
    if portfolio_dd >= DD_DEFENSIVE or sum(s <= 2 for s in tech_scores.values()) >= 2:
        return "defensive"
    if peak_profit_rate >= PROFIT_PROTECT_TRIGGER and portfolio_dd >= PROFIT_PULLBACK_TRIGGER:
        return "protect"
    if portfolio_dd < DD_WARN and sum(s >= 4 for s in tech_scores.values()) >= 2:
        return "offensive"
    return "neutral"
