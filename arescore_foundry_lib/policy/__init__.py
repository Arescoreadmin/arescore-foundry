"""Helpers for working with Open Policy Agent (OPA) policies.

The production deployment ships the Rego policies that live in ``policies/``
and ``_container_policies/`` to the shared OPA sidecar.  Several services import
``arescore_foundry_lib.policy`` expecting a couple of utilities to exist for
loading those Rego files, building bundles, and optionally publishing them to a
running OPA instance.  The original repository layout never committed this
module which made local development inconvenient – importing ``app.main`` would
crash with ``ImportError: No module named 'arescore_foundry_lib'``.  This module
fills that gap with a small, dependency-light implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import re
from pathlib import Path
from typing import Any, Iterator, Mapping, MutableMapping, Sequence

__all__ = [
    "PolicyBundle",
    "AuditLogger",
    "OpaClient",
    "OpaDecision",
    "OpaDecisionDenied",
    "OpaError",
    "OpaConnectionError",
    "build_default_client",
]


class PolicyError(RuntimeError):
    """Base exception for policy related issues."""


class PolicyLoadError(PolicyError):
    """Raised when a policy file cannot be loaded or parsed."""


class PolicyPushError(PolicyError):
    """Raised when synchronising policy modules with OPA fails."""


_PACKAGE_RE = re.compile(r"^\s*package\s+([\w\.\/]+)", re.MULTILINE)


_HTTPX_MODULE: Any | None = None
_HTTPX_ATTEMPTED = False


@dataclass(frozen=True)
class PolicyModule:
    """A single Rego module discovered on disk."""

    package: str
    """The package identifier extracted from the module."""

    path: Path
    """Filesystem path pointing at the module."""

    source: str
    """Raw Rego source code."""

    def policy_id(self, prefix: str | None = None) -> str:
        """Return an identifier suitable for ``/v1/policies/{id}`` endpoints."""

        package = self.package.replace("/", ".").replace("..", ".")
        policy_id = package.replace(".", "/")
        if prefix:
            prefix = prefix.strip("/")
            policy_id = f"{prefix}/{policy_id}"
        return policy_id


def _extract_package(source: str, *, default: str | None = None) -> str:
    match = _PACKAGE_RE.search(source)
    if match:
        return match.group(1)
    if default:
        return default
    raise PolicyLoadError("Unable to determine package declaration from policy")


def load_policy_module(path: str | Path) -> PolicyModule:
    """Load a Rego policy module from disk."""

    module_path = Path(path)
    if not module_path.is_file():
        raise PolicyLoadError(f"Policy file not found: {module_path}")

    try:
        source = module_path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - filesystem failure guard
        raise PolicyLoadError(f"Failed to read policy file: {module_path}") from exc

    package = _extract_package(source, default=module_path.stem)
    return PolicyModule(package=package, path=module_path, source=source)


def discover_policy_modules(
    *roots: str | Path,
    pattern: str = "*.rego",
) -> list[PolicyModule]:
    """Discover and load every policy module stored under ``roots``."""

    modules: list[PolicyModule] = []
    seen_packages: set[str] = set()

    for root in roots or (Path.cwd(),):
        for file_path in sorted(Path(root).rglob(pattern)):
            if not file_path.is_file():
                continue
            module = load_policy_module(file_path)
            if module.package in seen_packages:
                raise PolicyLoadError(
                    f"Duplicate policy package detected: {module.package}"
                )
            modules.append(module)
            seen_packages.add(module.package)

    return modules


def build_policy_bundle(
    modules: Sequence[PolicyModule],
    *,
    data: Mapping[str, Any] | None = None,
) -> "PolicyBundle":
    """Create an immutable :class:`PolicyBundle` from modules and optional data."""

    return PolicyBundle(modules=tuple(modules), data=dict(data or {}))


@dataclass(frozen=True)
class PolicyBundle:
    """A logical bundle of modules with optional JSON data."""

    modules: tuple[PolicyModule, ...]
    data: MutableMapping[str, Any]

    @classmethod
    def from_directories(
        cls, *roots: str | Path, data: Mapping[str, Any] | None = None
    ) -> "PolicyBundle":
        modules = discover_policy_modules(*roots)
        return cls(modules=tuple(modules), data=dict(data or {}))

    def module_map(self) -> dict[str, str]:
        """Return a mapping of package name to source."""

        return {module.package: module.source for module in self.modules}

    def to_dict(self) -> dict[str, Any]:
        """Represent the bundle in the shape expected by OPA bundle APIs."""

        payload: dict[str, Any] = {
            "modules": [
                {
                    "package": module.package,
                    "path": str(module.path),
                    "source": module.source,
                }
                for module in self.modules
            ]
        }
        if self.data:
            payload["data"] = self.data
        return payload

    def to_json(self, *, indent: int | None = None) -> str:
        """Return a JSON string representation of the bundle."""

        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def __iter__(self) -> Iterator[PolicyModule]:
        return iter(self.modules)


class OPAClient:
    """Minimal HTTP client used for synchronising policies with OPA."""

    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def publish_bundle(
        self, bundle: PolicyBundle, *, prefix: str | None = None
    ) -> None:
        """Publish every module in ``bundle`` to the configured OPA instance."""

        if not self.base_url:
            raise PolicyPushError("OPA base URL must not be empty")

        errors: list[str] = []
        headers = {"Content-Type": "text/plain"}

        for module in bundle.modules:
            policy_id = module.policy_id(prefix)
            status, text = self._request(
                "PUT",
                f"/v1/policies/{policy_id}",
                headers=headers,
                content=module.source,
                error_cls=PolicyPushError,
            )
            if status >= 400:
                errors.append(f"{policy_id}: {status} {text.strip()}")

        if errors:
            raise PolicyPushError(
                "Failed to publish one or more policy modules: " + "; ".join(errors)
            )

    def evaluate(self, path: str, payload: Mapping[str, Any]) -> Any:
        """Invoke an OPA data API (``/v1/data/{path}``)."""

        if not self.base_url:
            raise PolicyError("OPA base URL must not be empty")

        endpoint = path.strip("/")
        url = f"{self.base_url}/v1/data/{endpoint}" if endpoint else f"{self.base_url}/v1/data"

        status, text = self._request(
            "POST",
            url,
            json_payload={"input": payload},
            error_cls=PolicyError,
        )
        if status >= 400:
            raise PolicyError(f"OPA evaluate request failed: {status} {text.strip()}")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PolicyError("OPA response was not valid JSON") from exc
        return data.get("result")

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        content: str | bytes | None = None,
        json_payload: Mapping[str, Any] | None = None,
        error_cls: type[PolicyError],
    ) -> tuple[int, str]:
        url = self._resolve_url(path)
        httpx_module = _get_httpx()
        if httpx_module is not None:
            request_headers = dict(headers or {})
            try:
                with httpx_module.Client(timeout=self.timeout) as client:
                    response = client.request(
                        method,
                        url,
                        headers=request_headers,
                        content=content,
                        json=json_payload,
                    )
            except httpx_module.HTTPError as exc:  # pragma: no cover - network guard
                raise error_cls(f"OPA request failed: {exc}") from exc
            return response.status_code, response.text

        return self._urllib_request(
            method,
            url,
            headers=headers,
            content=content,
            json_payload=json_payload,
            error_cls=error_cls,
        )

    def _resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def _urllib_request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        content: str | bytes | None,
        json_payload: Mapping[str, Any] | None,
        error_cls: type[PolicyError],
    ) -> tuple[int, str]:
        from urllib import error as urllib_error, request as urllib_request

        request_headers = dict(headers or {})
        data: bytes | None = None
        if json_payload is not None:
            data = json.dumps(json_payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        elif content is not None:
            data = content if isinstance(content, bytes) else content.encode("utf-8")

        req = urllib_request.Request(
            url,
            data=data,
            headers=request_headers,
            method=method.upper(),
        )

        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                status = response.getcode() or 0
                body = response.read()
        except urllib_error.HTTPError as exc:
            status = exc.code
            body = exc.read()
        except urllib_error.URLError as exc:  # pragma: no cover - network guard
            raise error_cls(f"OPA request failed: {exc.reason}") from exc

        return status, body.decode("utf-8", errors="replace")


def _get_httpx() -> Any | None:
    global _HTTPX_MODULE, _HTTPX_ATTEMPTED
    if not _HTTPX_ATTEMPTED:
        _HTTPX_ATTEMPTED = True
        try:  # pragma: no cover - optional dependency guard
            _HTTPX_MODULE = importlib.import_module("httpx")
        except Exception:
            _HTTPX_MODULE = None
    return _HTTPX_MODULE

