from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..ledger import (
    account_snapshot, latest_navs, nav_changes, open_lots, shares_by_fund,
)
from ..live import fetch_etf_live_price, fetch_fund_estimates
from ..models import WeeklySignal

import json

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    snap = account_snapshot(db)
    shares = shares_by_fund(db)
    navs = latest_navs(db)
    changes = nav_changes(db)
    funds = []
    for code, fund in FUNDS.items():
        value = snap["holdings"].get(code, 0.0)
        nav_date, nav_val = navs.get(code, (None, None))
        change = changes.get(code)
        daily_return = 0.0
        daily_pnl = 0.0
        if change and nav_val:
            _latest_date, latest_nav, _prev_date, prev_nav = change
            if prev_nav:
                daily_return = (latest_nav - prev_nav) / prev_nav
                daily_pnl = float(shares.get(code, 0.0)) * (latest_nav - prev_nav)
        funds.append({
            "code": code,
            "name": fund.name,
            "shares": round(shares.get(code, 0.0), 2),
            "nav": nav_val,
            "nav_date": nav_date.isoformat() if nav_date else None,
            "value": round(value, 2),
            "weight": round(value / snap["total_value"], 4) if snap["total_value"] else 0.0,
            "daily_return": round(daily_return, 4),
            "daily_pnl": round(daily_pnl, 2),
            "lots": open_lots(db, code, date.today()),
        })
    return {"funds": funds, "account": snap}


@router.get("/portfolio/live")
def portfolio_live(db: Session = Depends(get_db)):
    """盘中估算：仅对持有份额 > 0 的基金获取实时估算/ETF 价格。"""
    snap = account_snapshot(db)
    shares = shares_by_fund(db)
    held_codes = [code for code, q in shares.items() if q > 0]

    estimates = fetch_fund_estimates(held_codes)
    funds = []
    total_pnl = 0.0
    total_value = snap["total_value"]
    as_of = None
    for code in held_codes:
        qty = float(shares.get(code, 0.0))
        est = estimates.get(code)
        if est:
            live_value = qty * est["nav"]
            # 估算盈亏 = (估算净值 - 昨收净值) * 份额
            base_nav = est.get("previous_nav") or (est["nav"] / (1 + est["change_pct"]) if est["change_pct"] != -1 else est["nav"])
            pnl = qty * (est["nav"] - base_nav) if base_nav else 0.0
            total_pnl += pnl
            total_value = total_value - snap["holdings"].get(code, 0.0) + live_value
            funds.append({
                "code": code,
                "name": FUNDS[code].name,
                "estimated_nav": round(est["nav"], 4),
                "change_pct": round(est["change_pct"], 4),
                "estimated_value": round(live_value, 2),
                "estimated_pnl": round(pnl, 2),
                "time": est.get("time"),
                "has_estimate": True,
            })
            if est.get("time") and (as_of is None or est["time"] > as_of):
                as_of = est["time"]
        elif code == "027521":
            # 广发联接的代理 ETF 589210 有实时价格，可近似估算联接基金
            etf = fetch_etf_live_price("589210")
            if etf:
                base_nav = snap["holdings"].get(code, 0.0) / qty if qty else 0.0
                # 用 ETF 涨跌幅近似估算联接基金净值
                estimated_nav = base_nav * (1 + etf["change_pct"]) if base_nav else None
                if estimated_nav:
                    live_value = qty * estimated_nav
                    pnl = qty * (estimated_nav - base_nav)
                    total_pnl += pnl
                    total_value = total_value - snap["holdings"].get(code, 0.0) + live_value
                    funds.append({
                        "code": code,
                        "name": FUNDS[code].name,
                        "estimated_nav": round(estimated_nav, 4),
                        "change_pct": round(etf["change_pct"], 4),
                        "estimated_value": round(live_value, 2),
                        "estimated_pnl": round(pnl, 2),
                        "time": etf.get("time"),
                        "has_estimate": True,
                        "note": "按 589210 ETF 实时价格估算",
                    })
                    if etf.get("time") and (as_of is None or etf["time"] > as_of):
                        as_of = etf["time"]
                    continue
        funds.append({
            "code": code,
            "name": FUNDS[code].name,
            "estimated_nav": None,
            "change_pct": None,
            "estimated_value": snap["holdings"].get(code, 0.0),
            "estimated_pnl": None,
            "time": None,
            "has_estimate": False,
        })

    return {
        "as_of": as_of,
        "funds": funds,
        "total_estimated_value": round(total_value, 2),
        "total_estimated_pnl": round(total_pnl, 2),
    }


@router.get("/rebalance")
def rebalance(db: Session = Depends(get_db)):
    row = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    if row is None:
        return {"deviations": []}
    report = json.loads(row.report_json)
    total = report["total_value"]
    deviations = []
    for d in report["decisions"]:
        current_w = d["current_value"] / total if total else 0.0
        diff = d["target_weight"] - current_w
        deviations.append({
            "code": d["code"],
            "current_weight": round(current_w, 4),
            "target_weight": round(d["target_weight"], 4),
            "diff_pp": round(diff * 100, 2),
            "structural": abs(diff) >= 0.05,  # PDF 月度复核：≥5pp 才结构性调仓
        })
    return {"deviations": deviations}
