"""Minimal telemetry helpers for the orchestrator service."""

from __future__ import annotations

import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)


def emit_event(event_name: str, payload: Dict[str, Any]) -> None:
    """Emit a telemetry event.

    For now we simply log the event. The implementation can be expanded later to
    integrate with the real telemetry pipeline (NATS, OPA, etc.).
    """

    logger.info("event=%s payload=%s", event_name, payload)
