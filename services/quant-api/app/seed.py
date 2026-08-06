from sqlalchemy.orm import Session
from quant_core.config import FUNDS

from .models import Fund


def seed_funds(db: Session) -> None:
    for f in FUNDS.values():
        if db.get(Fund, f.code) is None:
            db.add(Fund(code=f.code, name=f.name, bucket=f.bucket,
                        role=f.role, cap=f.cap, proxy_code=f.proxy_code))
    db.commit()
