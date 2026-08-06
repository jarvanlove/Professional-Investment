"""指标计算。约定：nav 为按日期升序的日净值 Series；回撤用正值表示低于高点的比例。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ma(nav: pd.Series, window: int) -> float:
    if len(nav) < window:
        raise ValueError(f"need >= {window} points, got {len(nav)}")
    return float(nav.iloc[-window:].mean())


def period_return(nav: pd.Series, n: int) -> float:
    if len(nav) < n + 1:
        raise ValueError(f"need >= {n + 1} points, got {len(nav)}")
    return float(nav.iloc[-1] / nav.iloc[-1 - n] - 1)


def realized_vol(nav: pd.Series, window: int = 20, trading_days: int = 252) -> float:
    rets = nav.pct_change().dropna().iloc[-window:]
    if len(rets) < window:
        raise ValueError(f"need >= {window} returns, got {len(rets)}")
    return float(rets.std(ddof=1) * np.sqrt(trading_days))


def drawdown_from_high(nav: pd.Series, window: int = 20) -> float:
    """最新净值低于 window 内最高净值的比例（>=0）。"""
    if len(nav) < 1:
        raise ValueError("empty nav series")
    high = float(nav.iloc[-window:].max())
    return float(1 - nav.iloc[-1] / high)


def last_daily_return(nav: pd.Series) -> float:
    if len(nav) < 2:
        raise ValueError("need >= 2 points")
    return float(nav.iloc[-1] / nav.iloc[-2] - 1)
