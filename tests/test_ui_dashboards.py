import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from api import ui
from api.storage import ControlInvariant, DashboardStore, Decision, build_chain


def build_store() -> DashboardStore:
    tenant_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    tenant_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    decisions = [
        Decision(
            id="dec-a-1",
            tenant_id=tenant_a,
            created_at=created_at,
            status="deny",
            policy="network-egress",
            reason="Blocked outbound",
            actor="engine",
            metadata={"severity": "high"},
        ),
        Decision(
            id="dec-b-1",
            tenant_id=tenant_b,
            created_at=created_at,
            status="allow",
            policy="device-attest",
            reason="Verified",
            actor="engine",
            metadata={"severity": "low"},
        ),
    ]
    chain_a = build_chain(tenant_a, [{"event": "decision", "id": "dec-a-1"}])
    chain_b = build_chain(tenant_b, [{"event": "decision", "id": "dec-b-1"}])
    controls = [
        ControlInvariant(
            id="inv-a",
            tenant_id=tenant_a,
            name="Invariant A",
            status="healthy",
            remediation="Keep steady.",
            evidence_links=["/ui/decision/dec-a-1"],
        ),
        ControlInvariant(
            id="inv-b",
            tenant_id=tenant_b,
            name="Invariant B",
            status="at_risk",
            remediation="Fix soon.",
            evidence_links=["/ui/decision/dec-b-1"],
        ),
    ]
    return DashboardStore(decisions=decisions, chain=chain_a + chain_b, controls=controls)


def headers(tenant_id: uuid.UUID, scopes: list[str]) -> dict:
    return {
        "X-Tenant-ID": str(tenant_id),
        "X-Scopes": " ".join(scopes),
        "X-Subject": "tester",
    }


def test_tenant_scoping_for_decisions():
    store = build_store()
    ui.app.dependency_overrides[ui.get_store] = lambda: store
    client = TestClient(ui.app)

    tenant_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    response = client.get("/ui/decisions", headers=headers(tenant_a, ["ui:decisions:read"]))
    assert response.status_code == 200
    payload = response.json()
    assert all(item["id"].startswith("dec-a") for item in payload["items"])

    tenant_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    response = client.get("/ui/decisions", headers=headers(tenant_b, ["ui:decisions:read"]))
    payload = response.json()
    assert all(item["id"].startswith("dec-b") for item in payload["items"])
    ui.app.dependency_overrides = {}


def test_scope_enforcement_blocks_missing_scope():
    store = build_store()
    ui.app.dependency_overrides[ui.get_store] = lambda: store
    client = TestClient(ui.app)
    tenant_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    response = client.get("/ui/posture", headers=headers(tenant_a, []))
    assert response.status_code == 403
    ui.app.dependency_overrides = {}


def test_chain_verification_pass_and_fail():
    store = build_store()
    ui.app.dependency_overrides[ui.get_store] = lambda: store
    client = TestClient(ui.app)
    tenant_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    response = client.get(
        "/ui/forensics/chain/verify", headers=headers(tenant_a, ["ui:forensics:read"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == "PASS"

    store.chain[0].hash = "tampered"
    response = client.get(
        "/ui/forensics/chain/verify", headers=headers(tenant_a, ["ui:forensics:read"])
    )
    assert response.status_code == 200
    assert response.json()["status"] == "FAIL"
    ui.app.dependency_overrides = {}


def test_evidence_pack_manifest_deterministic(tmp_path: Path, monkeypatch):
    store = build_store()
    ui.app.dependency_overrides[ui.get_store] = lambda: store
    client = TestClient(ui.app)
    tenant_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    monkeypatch.setenv("UI_PACKETS_DIR", str(tmp_path))

    response = client.post("/ui/audit/packet", headers=headers(tenant_a, ["ui:audit:export"]))
    assert response.status_code == 200
    payload = response.json()
    token_one = payload["token"]
    manifest_files = {item["file"] for item in payload["manifest"]["files"]}
    assert {"decisions.jsonl", "chain_verification.json"}.issubset(manifest_files)
    bundle_path = Path(payload["path"])
    assert (bundle_path / "manifest.json").exists()

    response = client.post("/ui/audit/packet", headers=headers(tenant_a, ["ui:audit:export"]))
    payload_two = response.json()
    assert token_one == payload_two["token"]
    ui.app.dependency_overrides = {}
