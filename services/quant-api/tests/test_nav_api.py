from datetime import date, timedelta

import pandas as pd
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


def test_import_and_get(client):
    today = date.today()
    rows = [{"date": (today - timedelta(days=i)).isoformat(), "nav": 1.0 + i * 0.001}
            for i in range(5)]
    r = client.post("/api/nav/import", json={"fund_code": "001480", "rows": rows})
    assert r.status_code == 201 or r.status_code == 200
    assert r.json()["added"] == 5
    # 重复导入幂等
    assert client.post("/api/nav/import",
                       json={"fund_code": "001480", "rows": rows}).json()["added"] == 0
    data = client.get("/api/nav/001480").json()
    assert data["stale"] is False
    assert len(data["rows"]) == 5
    assert all(row["source"] == "manual" for row in data["rows"])


def test_stale_flag(client):
    old = (date.today() - timedelta(days=30)).isoformat()
    client.post("/api/nav/import",
                json={"fund_code": "005052", "rows": [{"date": old, "nav": 1.0}]})
    assert client.get("/api/nav/005052").json()["stale"] is True


def test_refresh_partial_failure(client, monkeypatch):
    import app.routers.nav as nav_router

    def ok(code):
        return pd.Series({date.today(): 1.5})

    def boom(code):
        raise RuntimeError("network down")

    monkeypatch.setattr(nav_router, "fetch_fund_nav", ok)
    monkeypatch.setattr(nav_router, "fetch_etf_nav", boom)
    r = client.post("/api/nav/refresh")
    assert r.status_code == 200
    results = {x["code"]: x for x in r.json()["results"]}
    assert results["001480"]["status"] == "ok"
    assert results["589210"]["status"] == "error"
