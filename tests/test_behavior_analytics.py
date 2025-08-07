import importlib

import responses
from fastapi.testclient import TestClient


def make_client(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_URL", "http://orchestrator")
    monkeypatch.setenv("LOG_INDEXER_URL", "http://log")
    monkeypatch.setenv("AUTH_TOKEN", "token")
    monkeypatch.setenv("ANOMALY_THRESHOLD", "0.5")
    import behavior_analytics.config as config
    importlib.reload(config)
    config.get_settings.cache_clear()
    import behavior_analytics.main as main
    importlib.reload(main)
    return TestClient(main.app)


def test_anomaly_detection(monkeypatch):
    client = make_client(monkeypatch)
    with responses.RequestsMock() as rsps:
        rsps.post("http://log", status=200)
        rsps.post("http://orchestrator/alerts", status=200)
        r = client.post("/events", json={"value": 0.8})
        assert r.json()["status"] == "anomaly"
        assert rsps.calls[-1].request.headers["Authorization"] == "Bearer token"


def test_normal_event(monkeypatch):
    client = make_client(monkeypatch)
    with responses.RequestsMock() as rsps:
        rsps.post("http://log", status=200)
        r = client.post("/events", json={"value": 0.1})
        assert r.json()["status"] == "ok"
        assert len(rsps.calls) == 1


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_URL", "http://o")
    monkeypatch.setenv("LOG_INDEXER_URL", "http://l")
    monkeypatch.setenv("AUTH_TOKEN", "secret")
    monkeypatch.setenv("ANOMALY_THRESHOLD", "0.7")
    import behavior_analytics.config as config
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.orchestrator_url == "http://o"
    assert settings.log_indexer_url == "http://l"
    assert settings.auth_token == "secret"
    assert settings.anomaly_threshold == 0.7
