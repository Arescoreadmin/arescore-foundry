from __future__ import annotations

from pathlib import Path

import pytest

from arescore_foundry_lib.policy import (
    PolicyBundle,
    PolicyLoadError,
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

