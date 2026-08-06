import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def test_deposit_then_buy_flow(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "deposit", "amount": 19044.07,
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 2107.85, "shares": 1500.0, "nav": 1.4052, "reason_code": "B1",
    })
    assert r.status_code == 201, r.text
    trades = client.get("/api/trades").json()
    assert len(trades) == 2


def test_buy_requires_fund_fields(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "amount": 1000.0,
    })
    assert r.status_code == 422


def test_invalid_reason_code_rejected(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 1000.0, "shares": 700.0, "nav": 1.43, "reason_code": "X9",
    })
    assert r.status_code == 422
