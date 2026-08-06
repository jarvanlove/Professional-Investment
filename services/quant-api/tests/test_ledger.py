"""账本峰值口径：出金不应产生幻影回撤（峰值按净投入流量调整）。"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ledger import account_snapshot
from app.models import Base, Trade, WeeklySignal


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_withdraw_after_peak_does_not_create_phantom_drawdown(db):
    db.add(Trade(date=date(2026, 7, 1), direction="deposit", amount=20000.0))
    # 峰值快照：当时总值 20000、净投入 20000
    db.add(WeeklySignal(as_of=date(2026, 7, 31), report_json="{}",
                        total_value=20000.0, net_contributed=20000.0))
    db.add(Trade(date=date(2026, 8, 3), direction="withdraw", amount=5000.0))
    db.commit()
    snap = account_snapshot(db)
    assert snap["total_value"] == pytest.approx(15000.0)
    # 峰值流量调整：20000 + (15000 - 20000) = 15000 → 无幻影回撤
    assert snap["peak_value"] == pytest.approx(15000.0)
    assert snap["portfolio_dd"] == pytest.approx(0.0)
