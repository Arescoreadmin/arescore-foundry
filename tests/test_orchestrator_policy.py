from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from arescore_foundry_lib.policy import OpaDecisionDenied
from services.orchestrator.app import main as orch_main


def test_orchestrator_ready_reports_version(monkeypatch):
    monkeypatch.setattr(orch_main, "OPA_CLIENT", SimpleNamespace(version="v123"))
    client = TestClient(orch_main.app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["policy_version"] == "v123"


def test_orchestrator_create_allows(monkeypatch):
    calls = []

    def allow(package: str, payload: dict):
        calls.append((package, payload))
        return SimpleNamespace(allow=True, reason="ok")

    monkeypatch.setattr(orch_main, "OPA_CLIENT", SimpleNamespace(ensure_allow=allow, version="v123"))
    client = TestClient(orch_main.app)
    scenario = {
        "name": "demo",
        "auth": {"issuer": "arescore-ca", "serial": "1"},
        "tokens": {"consent": {"signature": "sig", "model_hash": "m", "ttl_sec": 10}},
    }
    resp = client.post("/api/scenarios", json=scenario)
    assert resp.status_code == 200
    assert len(calls) == 2
    packages = {pkg for pkg, _ in calls}
    assert "foundry/authority" in packages
    assert "foundry/consent" in packages


def test_orchestrator_create_denied(monkeypatch):
    def deny(package: str, payload: dict):
        raise OpaDecisionDenied(package, {"allow": False, "reason": "revoked"})

    monkeypatch.setattr(orch_main, "OPA_CLIENT", SimpleNamespace(ensure_allow=deny, version="v123"))
    client = TestClient(orch_main.app)
    resp = client.post("/api/scenarios", json={"auth": {}, "tokens": {}})
    assert resp.status_code == 403
    assert "denied" in resp.json()["detail"]


def test_policy_bundle_endpoint(monkeypatch):
    bundle = orch_main._POLICY_BUNDLE
    client = TestClient(orch_main.app)
    resp = client.get("/api/policies/bundle")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == bundle.version
    assert body["bundle"]
