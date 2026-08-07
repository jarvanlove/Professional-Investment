from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, NavHistory

CODES = ("001480", "025343", "027521", "005052")


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def seed_navs(client):
    # 直接走 DB：为每只基金插入 80 个交易日的温和上行净值
    from app.db import get_db as _  # noqa
    override = app.dependency_overrides[get_db]
    db = next(iter([s for s in override()]))
    start = date.today() - timedelta(days=120)
    days = [start + timedelta(days=i) for i in range(80)]
    for code in CODES:
        for i, d in enumerate(days):
            db.add(NavHistory(fund_code=code, date=d,
                              nav=float(100 * 1.002 ** i), source="manual"))
    db.commit()
    db.close()


def test_compute_and_latest(client):
    seed_navs(client)
    client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "deposit", "amount": 19044.07})
    client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 2107.85, "shares": 1500.0, "nav": 1.4052, "reason_code": "B1"})
    r = client.post("/api/signals/compute")
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["regime"] in ("offensive", "neutral", "protect", "defensive")
    assert len(report["decisions"]) == 4
    assert all(d["reason_code"] in
               {"B1", "B2", "B3", "B4", "S1", "S2", "S3", "S4", "P1", "P2", "N0"}
               for d in report["decisions"])
    latest = client.get("/api/signals/latest")
    assert latest.status_code == 200
    assert latest.json()["as_of"] == report["as_of"]
    pf = client.get("/api/portfolio").json()
    assert pf["account"]["net_contributed"] == pytest.approx(19044.07)
    ct = next(f for f in pf["funds"] if f["code"] == "001480")
    assert ct["shares"] == pytest.approx(1500.0)
    assert len(ct["lots"]) == 1
    rb = client.get("/api/rebalance").json()
    assert len(rb["deviations"]) == 4


def test_compute_without_data_returns_422(client):
    r = client.post("/api/signals/compute")
    assert r.status_code == 422


def test_latest_404_before_first_compute(client):
    assert client.get("/api/signals/latest").status_code == 404
