from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import AppSetting, Base, WeeklySignal


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
        c.testing_session = TestingSession
        yield c
    app.dependency_overrides.clear()


def _clear_env(monkeypatch):
    for v in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(v, raising=False)


def test_503_without_api_key(client, monkeypatch):
    _clear_env(monkeypatch)
    r = client.get("/api/settings/models")
    assert r.status_code == 503
    assert "未配置" in r.json()["detail"]


def test_success_returns_model_ids(client, monkeypatch):
    _clear_env(monkeypatch)
    db = client.testing_session()
    db.add(AppSetting(key="llm_api_key", value="sk-test"))
    db.commit()
    db.close()

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "object": "list",
                "data": [
                    {"id": "deepseek-v4-pro", "object": "model", "owned_by": "deepseek"},
                    {"id": "deepseek-v4-flash", "object": "model", "owned_by": "deepseek"},
                ],
            }

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    r = client.get("/api/settings/models")
    assert r.status_code == 200
    assert r.json()["models"] == ["deepseek-v4-pro", "deepseek-v4-flash"]


def test_502_on_provider_failure(client, monkeypatch):
    _clear_env(monkeypatch)
    db = client.testing_session()
    db.add(AppSetting(key="llm_api_key", value="sk-test"))
    db.commit()
    db.close()

    def boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(httpx, "get", boom)
    r = client.get("/api/settings/models")
    assert r.status_code == 502
    assert "connection reset" in r.json()["detail"]


def test_tolerant_parsing_missing_data(client, monkeypatch):
    _clear_env(monkeypatch)
    db = client.testing_session()
    db.add(AppSetting(key="llm_api_key", value="sk-test"))
    db.commit()
    db.close()

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"object": "list"}

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    r = client.get("/api/settings/models")
    assert r.status_code == 200
    assert r.json()["models"] == []


def test_preview_success(client, monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "object": "list",
                "data": [
                    {"id": "kimi-k3", "object": "model", "owned_by": "moonshot"},
                ],
            }

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    r = client.post("/api/settings/models-preview", json={
        "base_url": "https://api.moonshot.ai/v1",
        "api_key": "sk-test",
    })
    assert r.status_code == 200
    assert r.json()["models"] == ["kimi-k3"]


def test_preview_missing_key(client):
    r = client.post("/api/settings/models-preview", json={
        "base_url": "https://api.moonshot.ai/v1",
        "api_key": "",
    })
    assert r.status_code == 503
    assert "未配置" in r.json()["detail"]
