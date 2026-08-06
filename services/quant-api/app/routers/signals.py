import json
from dataclasses import asdict
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quant_core.config import FUNDS
from quant_core.engine import AccountState, build_signal_report

from ..db import get_db
from ..ledger import account_snapshot
from ..models import NavHistory, WeeklySignal

router = APIRouter(prefix="/api/signals", tags=["signals"])

MIN_POINTS = 61  # MA60 至少需要 61 个点（60 日收益）


def _load_series(db: Session, code: str) -> pd.Series:
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.fund_code == code)
        .order_by(NavHistory.date)
        .all()
    )
    return pd.Series({r.date: r.nav for r in rows}).sort_index()


def _navs_with_proxy(db: Session) -> tuple[dict[str, pd.Series], list[str]]:
    navs, notes = {}, []
    for code, fund in FUNDS.items():
        s = _load_series(db, code)
        if len(s) < MIN_POINTS and fund.proxy_code:
            s = _load_series(db, fund.proxy_code)
            notes.append(f"{code} 历史不足 {MIN_POINTS} 点，信号来自代理 ETF {fund.proxy_code}")
        navs[code] = s
    return navs, notes


@router.post("/compute")
def compute(db: Session = Depends(get_db)):
    navs, notes = _navs_with_proxy(db)
    short = [c for c, s in navs.items() if len(s) < MIN_POINTS]
    if short:
        raise HTTPException(422, detail={"error": "净值数据不足", "funds": short})
    snap = account_snapshot(db)
    account = AccountState(
        total_value=snap["total_value"], cash_value=snap["cash"],
        peak_value=snap["peak_value"], net_contributed=snap["net_contributed"],
        peak_profit_rate=snap["peak_profit_rate"],
    )
    last = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    prev_scores = None
    if last:
        prev = json.loads(last.report_json)
        prev_scores = {d["code"]: d["score"] for d in prev["decisions"]}
    # engine 对每只基金都做 holdings[code] 取值，缺仓位的基金需补 0
    holdings = {code: snap["holdings"].get(code, 0.0) for code in FUNDS}
    report = build_signal_report(navs, holdings, account,
                                 prev_scores=prev_scores)
    for note in notes:
        for d in report.decisions:
            if d.code in note:
                d.notes.append(note)
    payload = asdict(report)
    db.add(WeeklySignal(
        as_of=date.today(), report_json=json.dumps(payload, ensure_ascii=False),
        total_value=account.total_value, net_contributed=account.net_contributed,
    ))
    db.commit()
    return payload


@router.get("/latest")
def latest(db: Session = Depends(get_db)):
    row = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    if row is None:
        raise HTTPException(404, detail="尚无信号快照，请先 POST /api/signals/compute")
    return json.loads(row.report_json)
