"""Tests for the orchestrator MVP API surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import services.orchestrator.app.main as orchestrator_main
from arescore_foundry_lib.policy import PolicyBundle, PolicyModule, PolicyPushError


class FakeAuditLogger:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def log(
        self,
        *,
        service: str,
        snapshot_id: str | None,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.records.append(
            {
                "service": service,
                "snapshot_id": snapshot_id,
                "status": status,
                "details": dict(details or {}),
            }
        )


@pytest.fixture(autouse=True)
def configure_policy_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if hasattr(orchestrator_main.get_policy_audit_logger, "cache_clear"):
        orchestrator_main.get_policy_audit_logger.cache_clear()
    orchestrator_main.get_settings.cache_clear()
    monkeypatch.setenv(
        "FOUNDRY_ORCHESTRATOR_POLICY_AUDIT_LOG",
        str(tmp_path / "orchestrator-policy.jsonl"),
    )
    monkeypatch.setenv("FOUNDRY_ORCHESTRATOR_OPA_URL", "")
    yield
    if hasattr(orchestrator_main.get_policy_audit_logger, "cache_clear"):
        orchestrator_main.get_policy_audit_logger.cache_clear()
    orchestrator_main.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_scenarios() -> None:
    """Ensure the in-memory scenario store is isolated per test."""

    orchestrator_main.SCENARIOS.clear()
    yield
    orchestrator_main.SCENARIOS.clear()


def _create_client() -> TestClient:
    return TestClient(orchestrator_main.app)


def test_create_scenario_returns_identifier_and_persists_payload() -> None:
    client = _create_client()
    payload: dict[str, Any] = {
        "name": "Vault breach",
        "template": "standard",
        "description": "Baseline run for regression coverage",
        "objectives": ["exfiltrate"],
    }

    response = client.post("/api/scenarios", json=payload)

    assert response.status_code == 200
    scenario_id = response.json()["id"]

    assert scenario_id in orchestrator_main.SCENARIOS
    assert orchestrator_main.SCENARIOS[scenario_id] == payload

    stored = client.get(f"/api/scenarios/{scenario_id}")
    assert stored.status_code == 200
    assert stored.json() == {"id": scenario_id, "payload": payload}


def test_get_scenario_returns_404_for_unknown_identifier() -> None:
    client = _create_client()

    response = client.get("/api/scenarios/not-real")

    assert response.status_code == 404
    assert response.json() == {"detail": "Scenario not found"}


def test_create_scenario_emits_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _create_client()
    payload: dict[str, Any] = {
        "name": "Alpha",
        "template": "quickstart",
        "description": "Smoke test",
    }

    events: list[tuple[str, dict[str, Any]]] = []

    def capture(event_name: str, event_payload: dict[str, Any]) -> None:
        events.append((event_name, event_payload))

    monkeypatch.setattr("services.orchestrator.app.main.emit_event", capture)

    response = client.post("/api/scenarios", json=payload)

    assert response.status_code == 200
    scenario_id = response.json()["id"]

    assert events == [
        (
            "scenario.created",
            {
                "scenario_id": scenario_id,
                "name": "Alpha",
                "template": "quickstart",
                "description": "Smoke test",
            },
        )
    ]


def test_synchronise_policy_bundle_publishes_and_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    module = PolicyModule(
        package="demo.policy",
        path=Path("demo.rego"),
        source="package demo.policy\nallow := true\n",
    )
    bundle = PolicyBundle(modules=(module,), data={})

    monkeypatch.setattr(orchestrator_main, "load_policy_bundle", lambda: bundle)

    published: list[tuple[PolicyBundle, str | None]] = []

    class DummyClient:
        def publish_bundle(
            self, bundle: PolicyBundle, *, prefix: str | None = None
        ) -> None:
            published.append((bundle, prefix))

    monkeypatch.setattr(orchestrator_main, "create_opa_client", lambda: DummyClient())

    audit = FakeAuditLogger()
    monkeypatch.setattr(orchestrator_main, "get_policy_audit_logger", lambda: audit)
    monkeypatch.setenv("FOUNDRY_ORCHESTRATOR_OPA_URL", "http://opa:8181")
    orchestrator_main.get_settings.cache_clear()

    orchestrator_main.synchronise_policy_bundle()

    assert published == [
        (bundle, orchestrator_main.get_settings().opa_policy_prefix)
    ]
    assert audit.records[-1]["status"] == "published"
    assert audit.records[-1]["snapshot_id"]
    assert audit.records[-1]["details"]["module_count"] == 1


def test_synchronise_policy_bundle_skips_without_client(monkeypatch: pytest.MonkeyPatch) -> None:
    module = PolicyModule(
        package="demo.policy",
        path=Path("demo.rego"),
        source="package demo.policy\nallow := true\n",
    )
    bundle = PolicyBundle(modules=(module,), data={})

    monkeypatch.setattr(orchestrator_main, "load_policy_bundle", lambda: bundle)
    monkeypatch.setattr(orchestrator_main, "create_opa_client", lambda: None)

    audit = FakeAuditLogger()
    monkeypatch.setattr(orchestrator_main, "get_policy_audit_logger", lambda: audit)

    orchestrator_main.synchronise_policy_bundle()

    record = audit.records[-1]
    assert record["status"] == "skipped"
    assert record["details"]["reason"] == "OPA client not configured"
    assert record["details"]["module_count"] == 1


def test_synchronise_policy_bundle_logs_and_raises_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = PolicyModule(
        package="demo.policy",
        path=Path("demo.rego"),
        source="package demo.policy\nallow := true\n",
    )
    bundle = PolicyBundle(modules=(module,), data={})

    monkeypatch.setattr(orchestrator_main, "load_policy_bundle", lambda: bundle)

    class FailingClient:
        def publish_bundle(
            self, bundle: PolicyBundle, *, prefix: str | None = None
        ) -> None:
            raise PolicyPushError("boom")

    monkeypatch.setattr(orchestrator_main, "create_opa_client", lambda: FailingClient())

    audit = FakeAuditLogger()
    monkeypatch.setattr(orchestrator_main, "get_policy_audit_logger", lambda: audit)
    monkeypatch.setenv("FOUNDRY_ORCHESTRATOR_OPA_URL", "http://opa:8181")
    orchestrator_main.get_settings.cache_clear()

    with pytest.raises(PolicyPushError):
        orchestrator_main.synchronise_policy_bundle()

    record = audit.records[-1]
    assert record["status"] == "error"
    assert "boom" in record["details"]["error"]
