"""Messaging utilities backed by NATS."""

from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from nats.aio.client import Client as NATS  # type: ignore
except ImportError:  # pragma: no cover - optional dependency during type checking
    NATS = None  # type: ignore


class SpawnEvent(BaseModel):
    session_id: str
    topology_name: str
    plan: dict


class StatusUpdate(BaseModel):
    session_id: str
    state: str
    detail: Optional[str] = None


StatusHandler = Callable[[StatusUpdate], Awaitable[None]]


class EventBus:
    """Abstraction for orchestrator messaging."""

    async def start(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def stop(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def publish_spawn_event(self, event: SpawnEvent) -> None:  # pragma: no cover
        raise NotImplementedError

    async def publish_status_update(self, update: StatusUpdate) -> None:  # pragma: no cover
        raise NotImplementedError

    async def subscribe_to_status(self, handler: StatusHandler) -> None:  # pragma: no cover
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    """Simple in-memory event bus for testing."""

    def __init__(self) -> None:
        self._handlers: List[StatusHandler] = []
        self.spawn_events: list[SpawnEvent] = []
        self.status_updates: list[StatusUpdate] = []

    async def start(self) -> None:
        # Nothing to do
        return None

    async def stop(self) -> None:
        self._handlers.clear()

    async def publish_spawn_event(self, event: SpawnEvent) -> None:
        self.spawn_events.append(event)

    async def publish_status_update(self, update: StatusUpdate) -> None:
        self.status_updates.append(update)
        for handler in list(self._handlers):
            await handler(update)

    async def subscribe_to_status(self, handler: StatusHandler) -> None:
        self._handlers.append(handler)


class NATSBus(EventBus):
    """NATS backed event bus."""

    def __init__(self, url: str = "nats://localhost:4222") -> None:
        self._url = url
        self._nc: Optional[NATS] = None  # type: ignore[assignment]
        self._status_handlers: List[StatusHandler] = []
        self._status_subscription = None

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and getattr(self._nc, "is_connected", False)

    async def start(self) -> None:
        if NATS is None:
            logger.warning("nats-py is not installed; skipping NATS connection")
            return
        if self.is_connected:
            return
        self._nc = NATS()  # type: ignore[call-arg]
        try:
            await self._nc.connect(self._url)
            logger.info("Connected to NATS at %s", self._url)
        except Exception as exc:  # pragma: no cover - depends on runtime environment
            logger.error("Failed to connect to NATS: %s", exc)
            self._nc = None

    async def stop(self) -> None:
        if self._nc is None:
            return
        try:
            if self._status_subscription is not None:
                await self._status_subscription.unsubscribe()
            await self._nc.drain()
        finally:
            self._nc = None
            self._status_subscription = None

    async def publish_spawn_event(self, event: SpawnEvent) -> None:
        if self._nc is None:
            logger.debug("Dropping spawn event because NATS is not connected: %s", event.json())
            return
        await self._nc.publish("orchestrator.spawn", event.json().encode())

    async def publish_status_update(self, update: StatusUpdate) -> None:
        if self._nc is None:
            logger.debug("Dropping status update because NATS is not connected: %s", update.json())
            # Even if not connected ensure handlers run for deterministic behaviour.
            for handler in list(self._status_handlers):
                await handler(update)
            return
        await self._nc.publish("orchestrator.status", update.json().encode())

    async def subscribe_to_status(self, handler: StatusHandler) -> None:
        self._status_handlers.append(handler)
        if self._nc is None:
            return

        async def _callback(msg) -> None:  # type: ignore[no-untyped-def]
            try:
                payload = json.loads(msg.data.decode())
                update = StatusUpdate(**payload)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("Failed to decode status update: %s", exc)
                return
            for registered in list(self._status_handlers):
                await registered(update)

        self._status_subscription = await self._nc.subscribe("orchestrator.status", cb=_callback)


__all__ = [
    "EventBus",
    "InMemoryEventBus",
    "NATSBus",
    "SpawnEvent",
    "StatusUpdate",
]
