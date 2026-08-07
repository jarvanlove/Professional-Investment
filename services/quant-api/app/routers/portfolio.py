from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..ledger import (
    account_snapshot, latest_navs, nav_changes, open_lots, shares_by_fund,
)
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
