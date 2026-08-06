"""约束投影 Π_C：单只上限、科技合计上限（PDF 4.4 / 05 章相关性闸门）。"""
from __future__ import annotations

from .config import FUNDS, TECH_CODES, TECH_TOTAL_CAP, REGIME_WEIGHTS


def apply_caps(weights: dict[str, float], regime: str) -> dict[str, float]:
    out = {c: min(w, FUNDS[c].cap) for c, w in weights.items()}
    tech_total = sum(out[c] for c in TECH_CODES)
    regime_tech = sum(REGIME_WEIGHTS[regime][c] for c in TECH_CODES)
    cap = min(TECH_TOTAL_CAP, regime_tech)
    if tech_total > cap > 0:
        scale = cap / tech_total
        for c in TECH_CODES:
            out[c] *= scale
    return out
