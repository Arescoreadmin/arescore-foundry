from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from services.consent_registry.app import main as consent_main


client = TestClient(consent_main.app)


def reset_state() -> None:
    consent_main.consent_registry.clear()
    consent_main.crl_store.clear()


def test_training_optin_persists_subject_metadata() -> None:
    reset_state()

    response = client.post(
        "/consent/training/optin",
        json={"subject": "demo-user", "token": "dev-token", "metadata": {"cohort": "netplus"}},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "opted_in"
    assert payload["subject"] == "demo-user"
    assert payload["token"] == "dev-token"
    assert payload["metadata"] == {"cohort": "netplus"}
    # ensure ISO 8601 timestamp
    datetime.fromisoformat(payload["timestamp"].replace("Z", "+00:00"))

    follow_up = client.get("/consent/training/optin/demo-user")
    assert follow_up.status_code == 200
    assert follow_up.json()["token"] == "dev-token"


def test_crl_records_revocations() -> None:
    reset_state()

    first = client.post("/crl", json={"serial": "ABC123", "reason": "test"})
    assert first.status_code == 201

    second = client.post("/crl", json={"serial": "XYZ999"})
    assert second.status_code == 201

    crl_response = client.get("/crl")
    payload = crl_response.json()

    assert crl_response.status_code == 200
    assert payload["serials"] == ["ABC123", "XYZ999"]
    reasons = {entry["serial"]: entry["reason"] for entry in payload["revocations"]}
    assert reasons == {"ABC123": "test", "XYZ999": None}
