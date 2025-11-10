"""Application factory for the orchestrator service."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from .config import Settings
from .messaging import EventBus, InMemoryEventBus, NATSBus
from .routes import build_admin_router
from .services import SessionService
from .state import SessionStore
from .translator import TopologyTranslator


def create_app(
    settings: Optional[Settings] = None,
    *,
    event_bus: Optional[EventBus] = None,
    session_store: Optional[SessionStore] = None,
) -> FastAPI:
    """Instantiate the FastAPI application with configured dependencies."""

    settings = settings or Settings()

    store = session_store or SessionStore(Path(settings.session_store_path))
    bus: EventBus
    if event_bus is not None:
        bus = event_bus
    else:
        bus = NATSBus(url=settings.nats_url)

    translator = TopologyTranslator()
    service = SessionService(store=store, translator=translator, event_bus=bus)

    app = FastAPI(title="Arescore Orchestrator")

    admin_router = build_admin_router(service=service)
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    @app.on_event("startup")
    async def _startup() -> None:
        await bus.start()
        await bus.subscribe_to_status(service.handle_status_update)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await bus.stop()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


__all__ = ["create_app", "Settings", "SessionService"]
