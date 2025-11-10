from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.frostgatecore import ingest as ingest_mod


class DummyVectorStore:
    def __init__(self):
        self.calls = 0
        self.model_hash = "h"
        self.signature = "sig"
        self.runtime_id = "runtime-1"

    def ingest(self, doc_bytes: bytes) -> str:
        self.calls += 1
        return "doc-1"


def test_ingest_allows(monkeypatch):
    vector = DummyVectorStore()

    def allow(package: str, payload: dict):
        return SimpleNamespace(allow=True, reason="ok")

    monkeypatch.setattr(ingest_mod, "_OPA_CLIENT", SimpleNamespace(ensure_allow=allow))
    monkeypatch.setattr(ingest_mod, "cached_doc_ingest", lambda data, ingest_fn: ingest_fn(data))

    doc_id = ingest_mod.ingest_doc_idempotent(b"hello", vector)
    assert doc_id == "doc-1"
    assert vector.calls == 1


def test_ingest_denied(monkeypatch):
    vector = DummyVectorStore()

    def deny(package: str, payload: dict):
        raise ingest_mod.OpaDecisionDenied(package, {"allow": False, "reason": "revoked"})

    monkeypatch.setattr(ingest_mod, "_OPA_CLIENT", SimpleNamespace(ensure_allow=deny))
    monkeypatch.setattr(ingest_mod, "cached_doc_ingest", lambda data, ingest_fn: ingest_fn(data))

    with pytest.raises(PermissionError):
        ingest_mod.ingest_doc_idempotent(b"hello", vector)
