"""Lightweight configuration settings for the orchestrator service."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Runtime settings derived from environment variables."""

    nats_url: str = os.getenv("ORCHESTRATOR_NATS_URL", "nats://localhost:4222")
    session_store_path: str = os.getenv("ORCHESTRATOR_SESSION_STORE_PATH", "./data/sessions.json")


__all__ = ["Settings"]
