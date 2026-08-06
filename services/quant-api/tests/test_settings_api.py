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


def test_defaults_when_empty(client, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json() == {"llm_api_key": "", "llm_base_url": "https://api.deepseek.com",
                        "llm_model": "deepseek-v4-pro", "llm_provider": "deepseek"}


def test_update_and_persist(client):
    r = client.put("/api/settings", json={"llm_model": "deepseek-v4-flash",
                                          "llm_api_key": "sk-test",
                                          "llm_provider": "kimi"})
    assert r.status_code == 200
    assert r.json()["llm_model"] == "deepseek-v4-flash"
    assert r.json()["llm_provider"] == "kimi"
    assert client.get("/api/settings").json()["llm_api_key"] == "sk-test"


def test_unknown_key_rejected(client):
    r = client.put("/api/settings", json={"evil_key": "x"})
    assert r.status_code == 422


def test_env_fallback(client, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    assert client.get("/api/settings").json()["llm_api_key"] == "sk-from-env"
