"""Entry point for running the orchestrator application."""

from __future__ import annotations

from . import create_app

app = create_app()


__all__ = ["app", "create_app"]
