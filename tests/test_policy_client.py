from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from arescore_foundry_lib.policy import (
    AuditLogger,
    OpaClient,
    OpaDecisionDenied,
    PolicyBundle,
)

POLICY_ROOT = Path(__file__).resolve().parents[1] / "policies"


def test_policy_bundle_roundtrip():
    bundle = PolicyBundle.from_directory(POLICY_ROOT)
    assert bundle.version
    tarball = bundle.to_tarball()
    assert tarball
    encoded = bundle.to_base64()
    assert isinstance(encoded, str) and encoded
    manifest = bundle.manifest()
    assert manifest["version"] == bundle.version


def test_audit_logger_writes_jsonl(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(audit_path, service="test")
    logger.log(
        package="foundry/example",
        decision={"allow": True, "reason": "ok"},
        input_data={"foo": "bar"},
        version="123",
        elapsed_ms=4.2,
    )
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["allow"] is True
    assert record["version"] == "123"
    assert record["service"] == "test"


def test_opa_client_allow(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("decision")
        return httpx.Response(200, json={"result": {"allow": True, "reason": "ok"}})

    transport = httpx.MockTransport(handler)
    bundle = PolicyBundle.from_directory(POLICY_ROOT)
    client = OpaClient(bundle=bundle, audit_logger=None, sync_transport=transport, async_transport=transport)
    decision = client.ensure_allow("foundry/training_gate", {"track": "netplus", "dataset": {"id": "ds"}, "model": {"hash": "h"}, "tokens": {"consent": {"signature": "sig"}}})
    assert decision.allow is True


def test_opa_client_deny_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": {"allow": False, "reason": "nope"}})

    transport = httpx.MockTransport(handler)
    bundle = PolicyBundle.from_directory(POLICY_ROOT)
    client = OpaClient(bundle=bundle, audit_logger=None, sync_transport=transport, async_transport=transport)
    with pytest.raises(OpaDecisionDenied) as exc:
        client.ensure_allow("foundry/training_gate", {"track": "netplus", "dataset": {"id": "ds"}, "model": {"hash": "h"}, "tokens": {"consent": {"signature": "sig"}}})
    assert "nope" in str(exc.value)
