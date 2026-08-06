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
        c.testing_session = TestingSession  # 供用例直接种数据
        yield c
    app.dependency_overrides.clear()


def _seed_snapshot(client, report: dict | None = None):
    db = client.testing_session()
    db.add(WeeklySignal(as_of=date(2026, 8, 6),
                        report_json=__import__("json").dumps(
                            report or {"regime": "neutral", "decisions": []},
                            ensure_ascii=False),
                        total_value=19044.07, net_contributed=19044.07))
    db.commit()
    db.close()


def _clear_env(monkeypatch):
    for v in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(v, raising=False)


def test_404_without_snapshot(client):
    assert client.post("/api/interpret").status_code == 404


def test_503_without_api_key(client, monkeypatch):
    _clear_env(monkeypatch)
    _seed_snapshot(client)
    r = client.post("/api/interpret")
    assert r.status_code == 503
    assert "未配置" in r.json()["detail"]


def test_success_returns_text(client, monkeypatch):
    _clear_env(monkeypatch)
    _seed_snapshot(client)
    db = client.testing_session()
    db.add(AppSetting(key="llm_api_key", value="sk-test"))
    db.commit()
    db.close()

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "本周结论：…"}}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp())
    r = client.post("/api/interpret")
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "本周结论：…"
    assert body["model"] == "deepseek-chat"
    assert body["as_of"] == "2026-08-06"


def test_502_on_llm_failure(client, monkeypatch):
    _clear_env(monkeypatch)
    _seed_snapshot(client)
    db = client.testing_session()
    db.add(AppSetting(key="llm_api_key", value="sk-test"))
    db.commit()
    db.close()

    def boom(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(httpx, "post", boom)
    r = client.post("/api/interpret")
    assert r.status_code == 502
    assert "connection reset" in r.json()["detail"]
