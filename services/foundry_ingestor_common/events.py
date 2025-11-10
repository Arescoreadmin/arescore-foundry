"""Event publishing helpers."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional


class EventPublisher:
    """Abstract async publisher used for dependency injection."""

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class LoggingEventPublisher(EventPublisher):
    """Fallback publisher that just stores messages in memory for inspection."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        self.messages.append((subject, payload))


class NATSPublisher(EventPublisher):
    """Publish events to a NATS broker."""

    def __init__(self, servers: Optional[list[str]] = None) -> None:
        self._servers = servers or ["nats://localhost:4222"]
        self._client = None
        self._lock = asyncio.Lock()

    async def _get_client(self):
        async with self._lock:
            if self._client is None:
                from nats.aio.client import Client as NATS  # type: ignore

                client = NATS()
                await client.connect(servers=self._servers)
                self._client = client
        return self._client

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        client = await self._get_client()
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        await client.publish(subject, data)
