"""Minimal telemetry helpers for the orchestrator service."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


logger = logging.getLogger(__name__)

_SINK_ENV_VAR = "FOUNDRY_TELEMETRY_PATH"
_DEFAULT_SINK = Path("audits") / "foundry-events.jsonl"


def _resolve_sink_path() -> Path:
    """Return the telemetry sink path as an absolute :class:`~pathlib.Path`."""

    configured_path = os.environ.get(_SINK_ENV_VAR)
    sink_path = Path(configured_path).expanduser() if configured_path else _DEFAULT_SINK

    if not sink_path.is_absolute():
        sink_path = Path.cwd() / sink_path

    return sink_path


def _serialise_event(event_name: str, payload: Dict[str, Any]) -> str:
    """Convert an event to a JSON line string."""

    event = {
        "event": event_name,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return json.dumps(event, default=_fallback_serializer, separators=(",", ":"))


def _fallback_serializer(value: Any) -> str:
    """Best-effort JSON serialiser for unsupported payload types."""

    return repr(value)


def emit_event(event_name: str, payload: Dict[str, Any]) -> None:
    """Emit a telemetry event to both the log and the JSONL sink."""

    try:
        sink_path = _resolve_sink_path()
        sink_path.parent.mkdir(parents=True, exist_ok=True)

        with sink_path.open("a", encoding="utf-8") as sink_file:
            sink_file.write(f"{_serialise_event(event_name, payload)}\n")

    except Exception:  # pragma: no cover - defensive logging
        logger.exception("failed_to_write_telemetry event=%s", event_name)

    logger.info("event=%s payload=%s", event_name, payload)
