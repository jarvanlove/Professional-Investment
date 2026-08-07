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


def test_crud(client):
    r = client.post("/api/dca-plans", json={
        "fund_code": "001480", "frequency": "weekly", "amount": 1000,
        "day_of_week": 4,
    })
    assert r.status_code == 200
    plan = r.json()
    assert plan["fund_code"] == "001480"
    assert plan["amount"] == 1000

    plans = client.get("/api/dca-plans").json()
    assert len(plans) == 1

    updated = client.put(f"/api/dca-plans/{plan['id']}", json={
        "fund_code": "001480", "frequency": "monthly", "amount": 2000,
        "day_of_month": 15,
    })
    assert updated.status_code == 200
    assert updated.json()["frequency"] == "monthly"

    assert client.delete(f"/api/dca-plans/{plan['id']}").json()["ok"] is True
    assert len(client.get("/api/dca-plans").json()) == 0


def test_unknown_fund_rejected(client):
    r = client.post("/api/dca-plans", json={
        "fund_code": "999999", "frequency": "weekly", "amount": 1000, "day_of_week": 1,
    })
    assert r.status_code == 422


def test_weekly_requires_day_of_week(client):
    r = client.post("/api/dca-plans", json={
        "fund_code": "001480", "frequency": "weekly", "amount": 1000,
    })
    assert r.status_code == 422


def test_monthly_requires_day_of_month(client):
    r = client.post("/api/dca-plans", json={
        "fund_code": "001480", "frequency": "monthly", "amount": 1000,
    })
    assert r.status_code == 422
