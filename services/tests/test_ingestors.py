from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from services.foundry_ingestor_common import create_ingestor_app
from services.foundry_ingestor_common.events import LoggingEventPublisher
from services.foundry_ingestor_common.models import Device, NetworkSegment, Site, Snapshot


@pytest.fixture
def identity_app(tmp_path: Path):
    db_path = tmp_path / "identity.db"
    audit_path = tmp_path / "identity_audit.jsonl"
    schema_path = Path("services/foundry-identity-ingestor/schemas/identity_snapshot.schema.json")
    publisher = LoggingEventPublisher()
    app = create_ingestor_app(
        service_name="foundry-identity-ingestor",
        schema_path=schema_path,
        snapshot_category="identity",
        database_url=f"sqlite:///{db_path}",
        audit_log_path=audit_path,
        event_publisher=publisher,
    )
    return app, publisher, audit_path


def build_payload(snapshot_id: str = "snap-1") -> dict[str, object]:
    return {
        "snapshot_id": snapshot_id,
        "collected_at": "2024-05-10T12:00:00Z",
        "site": {
            "code": "HQ",
            "name": "Headquarters",
            "description": "Primary site",
            "metadata": {"region": "us-east"},
        },
        "network_segments": [
            {
                "code": "SEG-1",
                "name": "Segment 1",
                "cidr": "10.0.0.0/24",
                "metadata": {"tier": "prod"},
            }
        ],
        "devices": [
            {
                "code": "DEV-1",
                "hostname": "server-1",
                "segment_code": "SEG-1",
                "ip_address": "10.0.0.5",
                "device_type": "server",
                "metadata": {"os": "linux"},
            }
        ],
        "metadata": {"ingestor": "test"},
    }


def test_sync_ingests_and_emits_events(identity_app: tuple):
    app, publisher, audit_path = identity_app
    client = TestClient(app)

    response = client.post("/sync", json=build_payload())
    assert response.status_code == 202
    assert response.json()["version"] == 1

    SessionLocal = app.state.session_factory
    with SessionLocal() as session:
        site = session.execute(select(Site)).scalar_one()
        assert site.code == "HQ"

        segment = session.execute(select(NetworkSegment)).scalar_one()
        assert segment.site_id == site.id

        device = session.execute(select(Device)).scalar_one()
        assert device.hostname == "server-1"

        snapshot = session.execute(select(Snapshot)).scalar_one()
        assert snapshot.version == 1

    subjects = [subject for subject, _ in publisher.messages]
    assert subjects == ["snapshot.synced", "snapshot.identity.synced"]

    log_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert log_lines
    entry = json.loads(log_lines[-1])
    assert entry["status"] == "ingested"
    assert entry["details"]["version"] == 1


def test_sync_duplicate_snapshot_is_logged(identity_app: tuple):
    app, publisher, audit_path = identity_app
    client = TestClient(app)
    payload = build_payload()

    client.post("/sync", json=payload)
    response = client.post("/sync", json=payload)

    assert response.status_code == 202
    assert len(publisher.messages) == 2  # still only initial events

    log_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in log_lines]
    statuses = [entry["status"] for entry in entries]
    assert "duplicate" in statuses


def test_sync_assigns_incremental_versions(identity_app: tuple):
    app, publisher, audit_path = identity_app
    client = TestClient(app)

    first_payload = build_payload("snap-1")
    second_payload = build_payload("snap-2")

    response_first = client.post("/sync", json=first_payload)
    response_second = client.post("/sync", json=second_payload)

    assert response_first.json()["version"] == 1
    assert response_second.json()["version"] == 2

    SessionLocal = app.state.session_factory
    with SessionLocal() as session:
        versions = [row.version for row in session.execute(select(Snapshot)).scalars()]
    assert sorted(versions) == [1, 2]

    assert len(publisher.messages) == 4  # two events per snapshot

    log_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in log_lines]
    ingested_versions = [entry["details"]["version"] for entry in entries if entry["status"] == "ingested"]
    assert sorted(ingested_versions) == [1, 2]


def test_sync_validation_failure(identity_app: tuple):
    app, publisher, audit_path = identity_app
    client = TestClient(app)

    response = client.post("/sync", json={"snapshot_id": "bad"})
    assert response.status_code == 422

    assert not publisher.messages
    log_lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in log_lines]
    assert any(entry["status"] == "failed" for entry in entries)
