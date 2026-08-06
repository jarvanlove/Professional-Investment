# quant_core/scoring.py
"""0-5 趋势评分（PDF 06 章）。"""
from __future__ import annotations

import pandas as pd

from .config import SCORE_MULTIPLIERS
from .indicators import ma, period_return


def trend_score(nav: pd.Series) -> int:
    last = float(nav.iloc[-1])
    ma20 = ma(nav, 20)
    ma60 = ma(nav, 60)
    dev = last / ma20 - 1
    score = 0
    score += last > ma20                    # 短期趋势为正
    score += ma20 > ma60                    # 中期趋势为正
    score += period_return(nav, 20) > 0     # 月度动量为正
    score += period_return(nav, 60) > 0     # 季度动量为正
    score += -0.03 <= dev <= 0.08           # 无破位、无严重追高
    return int(score)


def score_multiplier(score: int) -> float:
    return SCORE_MULTIPLIERS[score]
