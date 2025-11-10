"""Audit logging helpers for policy decisions."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

__all__ = ["AuditLogger"]


class AuditLogger:
    """Write allow/deny decisions to a JSONL file."""

    def __init__(self, path: Path | str, service: str | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.service = service
        self._lock = threading.Lock()

    @classmethod
    def from_env(
        cls,
        *,
        service: str,
        env_var: str = "OPA_AUDIT_LOG",
        default_directory: Path | str | None = None,
    ) -> "AuditLogger":
        override = os.getenv(env_var)
        if override:
            return cls(Path(override), service=service)

        directory: Path
        if default_directory is None:
            directory = Path.cwd() / "audits"
        else:
            directory = Path(default_directory)

        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{service}.jsonl"
        return cls(directory / filename, service=service)

    def log(
        self,
        *,
        package: str,
        decision: Mapping[str, Any],
        input_data: Mapping[str, Any] | None,
        version: str | None,
        elapsed_ms: float,
    ) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "package": package,
            "allow": bool(decision.get("allow")),
            "reason": decision.get("reason"),
            "service": self.service,
            "version": version,
            "elapsed_ms": round(elapsed_ms, 3),
        }
        if input_data is not None:
            record["input"] = input_data

        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def __repr__(self) -> str:
        return f"AuditLogger(path={self.path!s})"
