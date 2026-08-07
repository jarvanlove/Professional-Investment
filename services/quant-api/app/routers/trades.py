from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Trade
from ..schemas import TradeIn, TradeOut, TradePage

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=TradePage)
def list_trades(
    fund_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Trade)
    if fund_code:
        q = q.filter(Trade.fund_code == fund_code)
    total = q.count()
    items = (
        q.order_by(Trade.date.desc(), Trade.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return TradePage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TradeOut, status_code=201)
def create_trade(payload: TradeIn, db: Session = Depends(get_db)):
    trade = Trade(**payload.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
