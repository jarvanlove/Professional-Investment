import json
from dataclasses import asdict
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quant_core.config import FUNDS
from quant_core.dca import DcaPlanCfg
from quant_core.engine import AccountState, build_signal_report

from ..db import get_db
from ..ledger import account_snapshot, open_lots
from ..models import DcaPlan, NavHistory, WeeklySignal
from ..settings import get_strategy_config

router = APIRouter(prefix="/api/signals", tags=["signals"])

MIN_POINTS = 61  # MA60 至少需要 61 个点（60 日收益）


def _clean(obj):
    """将 numpy 标量/布尔递归转换为原生 Python 类型，便于 json.dumps。"""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if hasattr(obj, "item"):
        return obj.item()
    return obj


def _load_series(db: Session, code: str) -> pd.Series:
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.fund_code == code)
        .order_by(NavHistory.date)
        .all()
    )
    return pd.Series({r.date: r.nav for r in rows}).sort_index()


def _navs_with_proxy(db: Session) -> tuple[dict[str, pd.Series], list[str], dict[str, bool]]:
    navs, notes, proxy_used = {}, [], {}
    for code, fund in FUNDS.items():
        s = _load_series(db, code)
        proxy_used[code] = False
        if len(s) < MIN_POINTS and fund.proxy_code:
            s = _load_series(db, fund.proxy_code)
            proxy_used[code] = True
            notes.append(f"{code} 历史不足 {MIN_POINTS} 点，信号来自代理 ETF {fund.proxy_code}")
        navs[code] = s
    return navs, notes, proxy_used


def _dca_plans(db: Session) -> tuple[DcaPlanCfg, ...]:
    rows = db.query(DcaPlan).filter(DcaPlan.active.is_(True)).all()
    return tuple(
        DcaPlanCfg(
            fund_code=r.fund_code,
            frequency=r.frequency,
            amount=r.amount,
            day_of_week=r.day_of_week,
            day_of_month=r.day_of_month,
            active=r.active,
        )
        for r in rows
    )


@router.post("/compute")
def compute(db: Session = Depends(get_db)):
    navs, notes, proxy_used = _navs_with_proxy(db)
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

    strategy = get_strategy_config(db)
    lots_by_fund = {code: open_lots(db, code, date.today()) for code in FUNDS}
    dca_plans = _dca_plans(db)

    report = build_signal_report(
        navs, holdings, account,
        prev_scores=prev_scores,
        as_of=date.today(),
        base_weights=strategy.base_weights,
        max_sell_ratio=strategy.max_sell_ratio,
        buffer_pp=strategy.buffer_pp,
        dca_plans=dca_plans,
        lots_by_fund=lots_by_fund,
        confidence_scaling=strategy.confidence_scaling,
        fee_aversion=strategy.fee_aversion,
        proxy_used=proxy_used,
    )
    for note in notes:
        for d in report.decisions:
            if d.code in note:
                d.notes.append(note)
    payload = _clean(asdict(report))
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
