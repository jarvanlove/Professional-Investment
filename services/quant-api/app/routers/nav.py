from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..fetcher import fetch_etf_nav, fetch_fund_nav
from ..models import NavHistory

router = APIRouter(prefix="/api/nav", tags=["nav"])

STALE_DAYS = 7


def _upsert_navs(db: Session, code: str, series: pd.Series, source: str) -> int:
    existing = {
        r[0] for r in db.query(NavHistory.date)
        .filter(NavHistory.fund_code == code).all()
    }
    added = 0
    for d, v in series.items():
        if d not in existing:
            db.add(NavHistory(fund_code=code, date=d, nav=float(v), source=source))
            added += 1
    db.commit()
    return added


@router.post("/refresh")
def refresh(db: Session = Depends(get_db)):
    results = []
    codes = set(FUNDS)
    for f in FUNDS.values():
        if f.proxy_code:
            codes.add(f.proxy_code)
    for code in sorted(codes):
        fn = fetch_fund_nav if code in FUNDS else fetch_etf_nav
        try:
            added = _upsert_navs(db, code, fn(code), "auto")
            results.append({"code": code, "status": "ok", "added": added})
        except Exception as exc:  # 单基金失败不影响其他
            results.append({"code": code, "status": "error", "added": 0,
                            "error": str(exc)[:200]})
    return {"results": results}


class NavRow(BaseModel):
    date: date
    nav: float


class NavImportIn(BaseModel):
    fund_code: str
    rows: list[NavRow]


@router.post("/import")
def import_navs(payload: NavImportIn, db: Session = Depends(get_db)):
    series = pd.Series({r.date: r.nav for r in payload.rows}).sort_index()
    return {"added": _upsert_navs(db, payload.fund_code, series, "manual")}


@router.get("/{code}")
def get_navs(code: str, days: int = 120, db: Session = Depends(get_db)):
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.fund_code == code)
        .order_by(NavHistory.date.desc())
        .limit(days)
        .all()
    )
    rows.reverse()
    latest = rows[-1].date if rows else None
    stale = latest is None or (date.today() - latest) > timedelta(days=STALE_DAYS)
    return {
        "code": code,
        "stale": stale,
        "rows": [{"date": r.date.isoformat(), "nav": r.nav, "source": r.source}
                 for r in rows],
    }
