"""akshare 抓取。天天基金/东财接口变动的唯一定位点——解析只许改这里。"""
from __future__ import annotations

import akshare as ak
import pandas as pd


def fetch_fund_nav(code: str) -> pd.Series:
    """场外基金单位净值，index=date，升序。"""
    df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    s = pd.Series(
        df["单位净值"].astype(float).to_numpy(),
        index=pd.to_datetime(df["净值日期"]).dt.date,
    )
    return s.sort_index()


def fetch_etf_nav(code: str) -> pd.Series:
    """ETF 日收盘价（备用数据源），index=date，升序。"""
    df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="")
    s = pd.Series(
        df["收盘"].astype(float).to_numpy(),
        index=pd.to_datetime(df["日期"]).dt.date,
    )
    return s.sort_index()
