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
    payload = client.get("/api/trades").json()
    assert payload["total"] == 2
    assert len(payload["items"]) == 2


def test_list_filter_by_fund_code(client):
    client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "buy", "fund_code": "001480",
        "amount": 1000, "shares": 100, "nav": 1.0, "reason_code": "B1",
    })
    client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "buy", "fund_code": "025343",
        "amount": 1000, "shares": 100, "nav": 1.0, "reason_code": "B1",
    })
    client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "deposit", "amount": 5000,
    })
    payload = client.get("/api/trades?fund_code=001480").json()
    assert payload["total"] == 1
    assert payload["items"][0]["fund_code"] == "001480"


def test_list_pagination(client):
    for i in range(5):
        client.post("/api/trades", json={
            "date": f"2026-08-{i+1:02d}", "direction": "buy", "fund_code": "001480",
            "amount": 1000, "shares": 100, "nav": 1.0, "reason_code": "B1",
        })
    payload = client.get("/api/trades?page=1&page_size=2").json()
    assert payload["total"] == 5
    assert len(payload["items"]) == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 2

    payload = client.get("/api/trades?page=2&page_size=2").json()
    assert len(payload["items"]) == 2
    assert payload["page"] == 2

    payload = client.get("/api/trades?page=3&page_size=2").json()
    assert len(payload["items"]) == 1
    assert payload["page"] == 3


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
