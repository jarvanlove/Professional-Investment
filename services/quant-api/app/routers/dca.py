from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..models import DcaPlan
from ..schemas import DcaPlanIn, DcaPlanOut

router = APIRouter(prefix="/api/dca-plans", tags=["dca"])


def _validate_plan(payload: DcaPlanIn) -> None:
    if payload.fund_code not in FUNDS:
        raise HTTPException(status_code=422, detail=f"未知基金代码: {payload.fund_code}")


@router.get("", response_model=list[DcaPlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.query(DcaPlan).order_by(DcaPlan.id.desc()).all()


@router.post("", response_model=DcaPlanOut)
def create_plan(payload: DcaPlanIn, db: Session = Depends(get_db)):
    _validate_plan(payload)
    plan = DcaPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/{plan_id}", response_model=DcaPlanOut)
def update_plan(plan_id: int, payload: DcaPlanIn, db: Session = Depends(get_db)):
    _validate_plan(payload)
    plan = db.get(DcaPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="定投计划不存在")
    for k, v in payload.model_dump().items():
        setattr(plan, k, v)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(DcaPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="定投计划不存在")
    db.delete(plan)
    db.commit()
    return {"ok": True}
