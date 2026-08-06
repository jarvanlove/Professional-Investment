from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Trade
from ..schemas import TradeIn, TradeOut

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=list[TradeOut])
def list_trades(db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.date.desc(), Trade.id.desc()).all()


@router.post("", response_model=TradeOut, status_code=201)
def create_trade(payload: TradeIn, db: Session = Depends(get_db)):
    trade = Trade(**payload.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
