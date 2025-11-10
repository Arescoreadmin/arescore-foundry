from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

import arescore_foundry_lib.policy as policy
from arescore_foundry_lib.policy import (
    AuditLogger,
    OPAClient,
    PolicyBundle,
    PolicyLoadError,
    PolicyModule,
    discover_policy_modules,
    load_policy_module,
)


def test_load_policy_module_extracts_package(tmp_path: Path) -> None:
    rego = tmp_path / "example.rego"
    rego.write_text("package demo.example\nallow = true\n", encoding="utf-8")

    module = load_policy_module(rego)

    assert module.package == "demo.example"
    assert module.path == rego
    assert "allow = true" in module.source


def test_load_policy_module_without_package_uses_filename(tmp_path: Path) -> None:
    rego = tmp_path / "fallback.rego"
    rego.write_text("default allow = false\n", encoding="utf-8")

    module = load_policy_module(rego)

    assert module.package == "fallback"


def test_discover_policy_modules_detects_duplicates(tmp_path: Path) -> None:
    rego_a = tmp_path / "a.rego"
    rego_a.write_text("package duplicate.test\nallow = true\n", encoding="utf-8")
    rego_b = tmp_path / "b.rego"
    rego_b.write_text("package duplicate.test\nallow = false\n", encoding="utf-8")

    with pytest.raises(PolicyLoadError):
        discover_policy_modules(tmp_path)


def test_bundle_from_directories_captures_repo_policies() -> None:
    bundle = PolicyBundle.from_directories("policies")

    packages = {module.package for module in bundle}
    assert "foundry.training_gate" in packages
    assert "foundry.runtime_revocation" in packages


def test_opa_client_publish_bundle_falls_back_to_urllib(monkeypatch: pytest.MonkeyPatch) -> None:
    module = PolicyModule(
        package="demo.example",
        path=Path("demo.rego"),
        source="package demo.example\nallow = true\n",
    )
    bundle = PolicyBundle(modules=(module,), data={})

    captured: list[tuple[str, str, dict[str, str], str | bytes | None, dict[str, Any] | None]] = []

    def fake_urllib(
        self: OPAClient,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        content: str | bytes | None,
        json_payload: Mapping[str, Any] | None,
        error_cls: type[Exception],
    ) -> tuple[int, str]:
        captured.append((method, url, dict(headers or {}), content, dict(json_payload or {})))
        return 204, ""

    monkeypatch.setattr(policy, "_get_httpx", lambda: None)
    monkeypatch.setattr(OPAClient, "_urllib_request", fake_urllib, raising=False)

    client = OPAClient("http://localhost:8181", timeout=0.1)
    client.publish_bundle(bundle)

    assert captured == [
        (
            "PUT",
            "http://localhost:8181/v1/policies/demo/example",
            {"Content-Type": "text/plain"},
            module.source,
            {},
        )
    ]


def test_opa_client_evaluate_falls_back_to_urllib(monkeypatch: pytest.MonkeyPatch) -> None:
    response_payload = {"result": {"allow": True}}

    def fake_urllib(
        self: OPAClient,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        content: str | bytes | None,
        json_payload: Mapping[str, Any] | None,
        error_cls: type[Exception],
    ) -> tuple[int, str]:
        assert method == "POST"
        assert url == "http://localhost:8181/v1/data/demo/allow"
        assert headers is None  # headers are populated inside the real urllib implementation
        assert dict(json_payload or {}) == {"input": {"value": 1}}
        return 200, json.dumps(response_payload)

    monkeypatch.setattr(policy, "_get_httpx", lambda: None)
    monkeypatch.setattr(OPAClient, "_urllib_request", fake_urllib, raising=False)

    client = OPAClient("http://localhost:8181", timeout=0.1)
    result = client.evaluate("demo/allow", {"value": 1})

    assert result == response_payload["result"]


def test_policy_client_module_reexports_public_api() -> None:
    module = __import__("arescore_foundry_lib.policy.client", fromlist=["OPAClient"])

    assert module.OPAClient is OPAClient
    assert module.PolicyBundle is PolicyBundle


def test_audit_logger_appends_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "audit" / "events.jsonl"
    logger = AuditLogger(log_path)

    logger.log(service="orchestrator", snapshot_id="123", status="ok", details={"k": "v"})

    contents = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(contents) == 1
    payload = json.loads(contents[0])
    assert payload["service"] == "orchestrator"
    assert payload["snapshot_id"] == "123"
    assert payload["status"] == "ok"
    assert payload["details"] == {"k": "v"}
    # Timestamp should exist and be ISO formatted to second granularity
    assert payload["timestamp"].endswith("Z") or payload["timestamp"].count(":") >= 2

