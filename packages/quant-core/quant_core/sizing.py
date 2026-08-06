"""目标权重：基准权重 × 评分乘数 × 波动率乘数，再受单只 cap 约束（PDF 4.4）。"""
from __future__ import annotations

from .config import FUNDS, REGIME_WEIGHTS
from .scoring import score_multiplier


def vol_multiplier(vol: float, bands: tuple[tuple[float, float], ...]) -> float:
    for upper, mult in bands:
        if vol < upper:
            return mult
    return bands[-1][1]


def base_weight(regime: str, code: str) -> float:
    return REGIME_WEIGHTS[regime][code]


def target_weight(regime: str, code: str, score: int, vol: float) -> float:
    fund = FUNDS[code]
    w = base_weight(regime, code) * score_multiplier(score) * vol_multiplier(vol, fund.vol_bands)
    return min(w, fund.cap)
