"""盘中估算数据源。天天基金 FundValuationLast + 新浪 ETF 行情。"""
from __future__ import annotations

import re
import requests


_TIANTIAN_API = "https://fundcomapi.tiantianfunds.com/mm/newCore/FundValuationLast"
_SINA_API = "https://hq.sinajs.cn/list={market}{code}"


def _market_for_stock(code: str) -> str:
    """沪市 sh / 深市 sz。ETF 默认上海；58/18 开头为深圳。"""
    if code.startswith(("00", "30", "15", "18")):
        return "sz"
    return "sh"


def fetch_fund_estimates(codes: list[str]) -> dict[str, dict]:
    """批量获取场外基金盘中估算。

    返回 {code: {"nav": float, "change_pct": float, "time": str|None, "source": str}}
    没有估算的基金不会出现在结果中。
    """
    if not codes:
        return {}

    fields = "FCODE,SHORTNAME,GSZZL,GZTIME,GSZ,NAV,PDATE"
    try:
        resp = requests.get(
            _TIANTIAN_API,
            params={"FCODES": ",".join(codes), "FIELDS": fields},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Referer": "https://fund.eastmoney.com/",
            },
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return {}

    out = {}
    for item in payload.get("data", []):
        fcode = item.get("FCODE")
        gsz = item.get("GSZ")
        gszzl = item.get("GSZZL")
        if not fcode or gsz is None or gszzl is None:
            continue
        try:
            out[fcode] = {
                "nav": float(gsz),
                "change_pct": float(gszzl) / 100,
                "time": item.get("GZTIME") or None,
                "previous_nav": float(item["NAV"]) if item.get("NAV") else None,
                "previous_date": item.get("PDATE") or None,
                "source": "tiantian",
            }
        except (ValueError, TypeError):
            continue
    return out


def fetch_etf_live_price(code: str) -> dict | None:
    """新浪 ETF 实时价格。返回 {"price": float, "change_pct": float, "time": str|None}。"""
    market = _market_for_stock(code)
    try:
        resp = requests.get(
            _SINA_API.format(market=market, code=code),
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=10,
        )
        resp.encoding = "gbk"
        text = resp.text
        if "var hq_str_" not in text:
            return None
        m = re.search(r'var hq_str_[^=]+="([^"]+)"', text)
        if not m:
            return None
        parts = m.group(1).split(",")
        if len(parts) < 3:
            return None
        # 格式：名称, 昨收, 今开, 最高, 最低, 最新, ...
        name = parts[0]
        prev_close = float(parts[1])
        latest = float(parts[3]) if parts[3] else float(parts[2])  # 最新价在 index 3 常见
        time_str = parts[-3] if len(parts) >= 3 else None
        return {
            "price": latest,
            "change_pct": (latest - prev_close) / prev_close if prev_close else 0.0,
            "time": time_str,
            "source": "sina",
        }
    except Exception:
        return None
