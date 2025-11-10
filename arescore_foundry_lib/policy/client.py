"""HTTP clients for querying OPA decisions."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

import httpx

from .audit import AuditLogger
from .bundle import PolicyBundle, discover_policy_root

__all__ = [
    "OpaClient",
    "OpaDecision",
    "OpaError",
    "OpaConnectionError",
    "OpaDecisionDenied",
    "build_default_client",
]


@dataclass(frozen=True)
class OpaDecision:
    allow: bool
    reason: str | None


class OpaError(RuntimeError):
    """Base exception for OPA client failures."""


class OpaConnectionError(OpaError):
    """Raised when the client cannot reach the OPA server."""


class OpaDecisionDenied(OpaError):
    """Raised when a policy evaluation returns allow=False."""

    def __init__(self, package: str, decision: Mapping[str, Any]):
        super().__init__(decision.get("reason") or "decision denied")
        self.package = package
        self.decision = decision

    @property
    def reason(self) -> str:
        val = self.decision.get("reason")
        return str(val) if val is not None else ""


class OpaClient:
    """HTTP client wrapper that understands decision objects."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = 5.0,
        audit_logger: AuditLogger | None = None,
        bundle: PolicyBundle | None = None,
        sync_transport: httpx.BaseTransport | None = None,
        async_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url or "http://opa:8181"
        self.timeout = timeout
        self.audit_logger = audit_logger
        self.bundle = bundle
        self._sync_transport = sync_transport
        self._async_transport = async_transport or sync_transport

    @property
    def version(self) -> str | None:
        return self.bundle.version if self.bundle else None

    def ensure_allow(self, package: str, input_data: Mapping[str, Any]) -> OpaDecision:
        decision = self.evaluate(package, input_data)
        if not decision.allow:
            raise OpaDecisionDenied(package, {"allow": decision.allow, "reason": decision.reason})
        return decision

    async def ensure_allow_async(self, package: str, input_data: Mapping[str, Any]) -> OpaDecision:
        decision = await self.evaluate_async(package, input_data)
        if not decision.allow:
            raise OpaDecisionDenied(package, {"allow": decision.allow, "reason": decision.reason})
        return decision

    def evaluate(self, package: str, input_data: Mapping[str, Any]) -> OpaDecision:
        payload = {"input": input_data}
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout, transport=self._sync_transport) as client:
                response = client.post(self._decision_url(package), json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - error path
            raise OpaConnectionError(str(exc)) from exc

        decision_map = self._parse_response(response.json())
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._emit_audit(package, decision_map, input_data, elapsed_ms)
        return OpaDecision(allow=bool(decision_map.get("allow")), reason=decision_map.get("reason"))

    async def evaluate_async(self, package: str, input_data: Mapping[str, Any]) -> OpaDecision:
        payload = {"input": input_data}
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout, transport=self._async_transport) as client:
                response = await client.post(self._decision_url(package), json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - error path
            raise OpaConnectionError(str(exc)) from exc

        decision_map = self._parse_response(response.json())
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._emit_audit(package, decision_map, input_data, elapsed_ms)
        return OpaDecision(allow=bool(decision_map.get("allow")), reason=decision_map.get("reason"))

    def _decision_url(self, package: str) -> str:
        package_path = package.strip("/")
        if package_path.endswith("/decision"):
            package_path = package_path[:-len("/decision")]
        return f"{self.base_url}/v1/data/{package_path}/decision"

    @staticmethod
    def _parse_response(raw: Mapping[str, Any]) -> Mapping[str, Any]:
        result = raw.get("result")
        if isinstance(result, Mapping):
            return result
        if isinstance(result, bool):
            return {"allow": result, "reason": None}
        raise OpaError("OPA response missing decision object")

    def _emit_audit(
        self,
        package: str,
        decision: Mapping[str, Any],
        input_data: Mapping[str, Any],
        elapsed_ms: float,
    ) -> None:
        if not self.audit_logger:
            return
        try:
            self.audit_logger.log(
                package=package,
                decision=decision,
                input_data=input_data,
                version=self.version,
                elapsed_ms=elapsed_ms,
            )
        except Exception:  # pragma: no cover - audit failures shouldn't break flow
            pass


def build_default_client(
    *,
    service: str,
    policy_dir: Optional[str | Path] = None,
    audit_env_var: str = "OPA_AUDIT_LOG",
) -> OpaClient:
    bundle = PolicyBundle.from_directory(policy_dir or discover_policy_root())
    default_dir = bundle.root.parent / "audits"
    audit = AuditLogger.from_env(service=service, env_var=audit_env_var, default_directory=default_dir)
    return OpaClient(bundle=bundle, audit_logger=audit)
