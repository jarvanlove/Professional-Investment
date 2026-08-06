"""从 trades 账本推导现金/份额/持仓/净投入。账本即真相，无冗余状态表。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import NavHistory, Trade, WeeklySignal


def _sums_by_direction(db: Session) -> dict[str, float]:
    rows = db.query(Trade.direction, func.sum(Trade.amount)).group_by(Trade.direction).all()
    return {d: float(s or 0.0) for d, s in rows}


def cash_balance(db: Session) -> float:
    s = _sums_by_direction(db)
    return s.get("deposit", 0.0) - s.get("withdraw", 0.0) - s.get("buy", 0.0) + s.get("sell", 0.0)


def net_contributed(db: Session) -> float:
    s = _sums_by_direction(db)
    return s.get("deposit", 0.0) - s.get("withdraw", 0.0)


def shares_by_fund(db: Session) -> dict[str, float]:
    out: dict[str, float] = {}
    rows = (
        db.query(Trade.fund_code, Trade.direction, func.sum(Trade.shares))
        .filter(Trade.fund_code.isnot(None))
        .group_by(Trade.fund_code, Trade.direction)
        .all()
    )
    for code, direction, total in rows:
        out.setdefault(code, 0.0)
        out[code] += float(total or 0.0) * (1 if direction == "buy" else -1)
    return out


def latest_navs(db: Session) -> dict[str, tuple[date, float]]:
    out: dict[str, tuple[date, float]] = {}
    codes = [r[0] for r in db.query(NavHistory.fund_code).distinct().all()]
    for code in codes:
        row = (
            db.query(NavHistory)
            .filter(NavHistory.fund_code == code)
            .order_by(NavHistory.date.desc())
            .first()
        )
        if row:
            out[code] = (row.date, row.nav)
    return out


def holdings_value(db: Session) -> dict[str, float]:
    shares = shares_by_fund(db)
    navs = latest_navs(db)
    return {c: sh * navs[c][1] for c, sh in shares.items() if c in navs and sh > 0}


def account_snapshot(db: Session) -> dict:
    """当前账户状态 + 历史峰值（峰值取自 weekly_signals 快照与当前值的较大者）。"""
    cash = cash_balance(db)
    contributed = net_contributed(db)
    holdings = holdings_value(db)
    total = cash + sum(holdings.values())
    peaks = [
        (s.total_value, s.net_contributed)
        for s in db.query(WeeklySignal).all()
    ] + [(total, contributed)]
    peak_value = max(p for p, _ in peaks if p > 0) if any(p > 0 for p, _ in peaks) else total
    profit_rates = [
        (p - c) / c for p, c in peaks if c > 0
    ]
    return {
        "cash": cash,
        "net_contributed": contributed,
        "holdings": holdings,
        "total_value": total,
        "peak_value": peak_value,
        "portfolio_dd": 1 - total / peak_value if peak_value > 0 else 0.0,
        "peak_profit_rate": max(profit_rates) if profit_rates else 0.0,
    }


def open_lots(db: Session, code: str, as_of: date) -> list[dict]:
    """FIFO 批次：买入为批次，卖出按先进先出冲销。用于持有天数与赎回费窗口。"""
    from quant_core.fees import redemption_fee_rate

    trades = (
        db.query(Trade)
        .filter(Trade.fund_code == code, Trade.direction.in_(["buy", "sell"]))
        .order_by(Trade.date, Trade.id)
        .all()
    )
    lots: list[dict] = []
    for t in trades:
        if t.direction == "buy":
            lots.append({"date": t.date, "shares": float(t.shares or 0.0)})
        else:
            remaining = float(t.shares or 0.0)
            while remaining > 1e-9 and lots:
                take = min(lots[0]["shares"], remaining)
                lots[0]["shares"] -= take
                remaining -= take
                if lots[0]["shares"] <= 1e-9:
                    lots.pop(0)
    return [
        {
            "buy_date": lot["date"].isoformat(),
            "shares": round(lot["shares"], 2),
            "holding_days": (as_of - lot["date"]).days,
            "fee_rate": redemption_fee_rate(code, (as_of - lot["date"]).days),
        }
        for lot in lots
    ]
