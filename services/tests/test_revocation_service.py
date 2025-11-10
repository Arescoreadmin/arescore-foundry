from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from services.revocation_service.app import main


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2024, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


@dataclass
class ServiceContext:
    client: TestClient
    clock: FakeClock
    registry: main.RevocationRegistry


@pytest.fixture
def service_context() -> ServiceContext:
    clock = FakeClock()
    registry = main.RevocationRegistry(now=clock.now)
    main.registry = registry
    main.registry.clear()
    main.registry.set_time_provider(clock.now)
    client = TestClient(main.app)
    return ServiceContext(client=client, clock=clock, registry=registry)


def test_health_endpoints(service_context: ServiceContext) -> None:
    assert service_context.client.get("/health").json() == {"ok": True}
    assert service_context.client.get("/live").json() == {"status": "alive"}
    ready = service_context.client.get("/ready").json()
    assert ready["status"] in {"ready", "degraded"}


def test_revocation_lifecycle(service_context: ServiceContext) -> None:
    payload = {"runtime_id": "r-123", "reason": "compromised"}
    response = service_context.client.post("/revocations/runtime", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["runtime_id"] == "r-123"
    assert created["reason"] == "compromised"
    assert created["expires_at"] is None

    listing = service_context.client.get("/revocations/runtime").json()
    assert listing["runtime_ids"] == ["r-123"]
    assert listing["entries"][0]["runtime_id"] == "r-123"

    delete_response = service_context.client.delete("/revocations/runtime/r-123")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"removed": True}

    empty_listing = service_context.client.get("/revocations/runtime").json()
    assert empty_listing["runtime_ids"] == []


def test_revocation_honors_ttl(service_context: ServiceContext) -> None:
    payload = {"runtime_id": "r-ttl", "reason": "ttl", "ttl_seconds": 30}
    assert service_context.client.post("/revocations/runtime", json=payload).status_code == 201

    listing = service_context.client.get("/revocations/runtime").json()
    assert listing["runtime_ids"] == ["r-ttl"]

    service_context.clock.advance(60)
    expired_listing = service_context.client.get("/revocations/runtime").json()
    assert expired_listing["runtime_ids"] == []


def test_reinstate_requires_identifier(service_context: ServiceContext) -> None:
    response = service_context.client.delete("/revocations/runtime/%20")
    assert response.status_code == 400
    assert response.json()["detail"] == "runtime_id must not be blank"
