from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.orchestrator.app import Settings, create_app
from backend.orchestrator.app.messaging import InMemoryEventBus
from backend.orchestrator.app.state import SessionStore


TOPOLOGY_YAML = """
name: api
containers:
  - name: web
    image: nginx:alpine
    interfaces:
      - network: net0
networks:
  - name: net0
links: []
"""


def build_test_app(tmp_path: Path) -> TestClient:
    settings = Settings(session_store_path=str(tmp_path / "sessions.json"))
    store = SessionStore(tmp_path / "sessions.json")
    bus = InMemoryEventBus()
    app = create_app(settings=settings, event_bus=bus, session_store=store)
    return TestClient(app)


def test_validate_template(tmp_path: Path) -> None:
    client = build_test_app(tmp_path)
    response = client.post("/admin/templates/validate", json={"topology": TOPOLOGY_YAML})
    assert response.status_code == 200
    payload = response.json()
    assert payload["containers"] == 1


def test_session_lifecycle(tmp_path: Path) -> None:
    client = build_test_app(tmp_path)
    response = client.post(
        "/admin/sessions",
        json={"name": "scenario", "topology": TOPOLOGY_YAML},
    )
    assert response.status_code == 200
    session = response.json()
    session_id = session["id"]

    list_response = client.get("/admin/sessions")
    assert list_response.status_code == 200
    assert any(item["id"] == session_id for item in list_response.json())

    state_response = client.post(
        f"/admin/sessions/{session_id}/state",
        json={"state": "active"},
    )
    assert state_response.status_code == 200

    detail_response = client.get(f"/admin/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == session_id
