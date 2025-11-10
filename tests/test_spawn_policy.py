from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from services.spawn_service.app import main as spawn_main
from arescore_foundry_lib.policy import OpaDecisionDenied


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        return SimpleNamespace(status_code=200, content=b"{}", json=lambda: {"id": "orch-1"})


def test_spawn_allows(monkeypatch):
    client = TestClient(spawn_main.app)

    async def allow_async(package: str, payload: dict):
        assert package == "foundry/training_gate"
        assert payload["track"] == "netplus"
        return SimpleNamespace(allow=True, reason="ok")

    monkeypatch.setattr(spawn_main, "OPA_CLIENT", SimpleNamespace(ensure_allow_async=allow_async))
    monkeypatch.setattr(spawn_main.httpx, "AsyncClient", DummyAsyncClient)

    resp = client.post(
        "/api/spawn",
        json={
            "track": "netplus",
            "dataset_id": "ds",
            "model_hash": "h",
            "consent_signature": "sig",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario_id"]


def test_spawn_denied(monkeypatch):
    client = TestClient(spawn_main.app)

    async def deny_async(package: str, payload: dict):
        raise OpaDecisionDenied(package, {"allow": False, "reason": "bad"})

    monkeypatch.setattr(spawn_main, "OPA_CLIENT", SimpleNamespace(ensure_allow_async=deny_async))
    monkeypatch.setattr(spawn_main.httpx, "AsyncClient", DummyAsyncClient)

    resp = client.post(
        "/api/spawn",
        json={
            "track": "netplus",
            "dataset_id": "ds",
            "model_hash": "h",
            "consent_signature": "sig",
        },
    )

    assert resp.status_code == 403
    assert "denied" in resp.json()["detail"]
