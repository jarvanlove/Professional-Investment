from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..settings import get_settings, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("")
def put_settings(payload: dict[str, str], db: Session = Depends(get_db)):
    try:
        return update_settings(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
