"""信号置信度：根据数据长度、代理使用、新鲜度和信号强度给出缩放系数。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd


@dataclass(frozen=True)
class Confidence:
    score: float  # 0..1
    level: str    # high | medium | low
    factors: list[str]


def _history_factor(nav: pd.Series) -> float:
    n = len(nav.dropna())
    if n >= 250:
        return 1.0
    if n >= 120:
        return 0.85
    if n >= 61:
        return 0.70
    return 0.4


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    # pandas Timestamp / datetime
    return value.date()


def _freshness_factor(nav: pd.Series, as_of: date) -> float:
    if nav.empty:
        return 0.5
    last = _to_date(nav.index[-1])
    days = (as_of - last).days
    if days <= 1:
        return 1.0
    if days <= 3:
        return 0.9
    if days <= 5:
        return 0.8
    return 0.6


def _strength_factor(score: int) -> float:
    if score in (0, 5):
        return 1.0
    if score in (1, 4):
        return 0.9
    return 0.8


def compute_confidence(
    nav: pd.Series,
    *,
    used_proxy: bool,
    score: int,
    as_of: date | None = None,
) -> Confidence:
    as_of = as_of or date.today()
    factors: list[str] = []
    score_conf = _history_factor(nav)
    if score_conf >= 1.0:
        factors.append("历史长度充足")
    elif score_conf >= 0.85:
        factors.append("历史长度中等")
    else:
        factors.append("历史长度偏短")

    if used_proxy:
        score_conf *= 0.8
        factors.append("使用代理 ETF 信号")

    fresh = _freshness_factor(nav, as_of)
    score_conf *= fresh
    if fresh >= 1.0:
        factors.append("净值数据最新")
    else:
        factors.append("净值数据滞后")

    strength = _strength_factor(score)
    score_conf *= strength
    factors.append(f"信号强度{'强' if strength >= 0.9 else '中等'}")

    score_conf = round(max(0.0, min(1.0, score_conf)), 4)
    if score_conf >= 0.75:
        level = "high"
    elif score_conf >= 0.5:
        level = "medium"
    else:
        level = "low"
    return Confidence(score=score_conf, level=level, factors=factors)
