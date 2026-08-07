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


def _clear_all_env(monkeypatch):
    for v in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "LLM_PROVIDER",
              "KIMI_API_KEY", "MINIMAX_API_KEY", "QWEN_API_KEY", "GLM_API_KEY"):
        monkeypatch.delenv(v, raising=False)


def test_defaults_when_empty(client, monkeypatch):
    _clear_all_env(monkeypatch)
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert r.json() == {
        "llm_api_key": "", "llm_base_url": "https://api.deepseek.com",
        "llm_model": "deepseek-v4-pro", "llm_provider": "deepseek",
        "deepseek_api_key": "", "kimi_api_key": "", "minimax_api_key": "",
        "qwen_api_key": "", "glm_api_key": "",
        "strategy_base_weights": '{"001480":0.08,"025343":0.04,"027521":0.0,"005052":0.10}',
        "strategy_max_sell_ratio": "0.30",
        "strategy_max_buy_ratio": "1.00",
        "strategy_buffer_pp": "0.02",
        "strategy_fee_aversion": "0.005",
        "strategy_confidence_scaling": "1",
    }


def test_update_and_persist(client):
    r = client.put("/api/settings", json={
        "llm_model": "deepseek-v4-flash",
        "llm_api_key": "sk-test",
        "llm_provider": "kimi",
        "deepseek_api_key": "sk-deepseek",
        "kimi_api_key": "sk-kimi",
    })
    assert r.status_code == 200
    assert r.json()["llm_model"] == "deepseek-v4-flash"
    assert r.json()["llm_provider"] == "kimi"
    assert r.json()["kimi_api_key"] == "sk-kimi"
    body = client.get("/api/settings").json()
    assert body["llm_api_key"] == "sk-test"
    assert body["deepseek_api_key"] == "sk-deepseek"
    assert body["kimi_api_key"] == "sk-kimi"


def test_unknown_key_rejected(client):
    r = client.put("/api/settings", json={"evil_key": "x"})
    assert r.status_code == 422


def test_env_fallback_for_llm_key(client, monkeypatch):
    _clear_all_env(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    assert client.get("/api/settings").json()["llm_api_key"] == "sk-from-env"


def test_env_fallback_for_provider_keys(client, monkeypatch):
    _clear_all_env(monkeypatch)
    monkeypatch.setenv("KIMI_API_KEY", "sk-kimi-env")
    assert client.get("/api/settings").json()["kimi_api_key"] == "sk-kimi-env"
