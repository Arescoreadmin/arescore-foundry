"""Tests for the orchestrator MVP API surface."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from ..main import SCENARIOS, app


@pytest.fixture(autouse=True)
def reset_scenarios() -> None:
    """Ensure the in-memory scenario store is isolated per test."""

    SCENARIOS.clear()
    yield
    SCENARIOS.clear()


def _create_client() -> TestClient:
    return TestClient(app)


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

    assert scenario_id in SCENARIOS
    assert SCENARIOS[scenario_id] == payload

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
