"""Common helpers for Foundry telemetry publishing and collection."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

__all__ = [
    "TelemetryConfig",
    "TelemetryEvent",
    "TelemetryPublisher",
    "TelemetrySubscriber",
    "TelemetryJSONLSink",
    "build_event",
    "serialise_event",
]

logger = logging.getLogger(__name__)

_DEFAULT_SUBJECT = "arescore.foundry.telemetry"
_DEFAULT_QUEUE = "arescore-foundry-audit"
_DEFAULT_SINK = Path("audits") / "foundry-events.jsonl"
_DEFAULT_NATS_URL = "nats://nats:4222"
_DEFAULT_CONNECT_TIMEOUT = 2.0
_DEFAULT_RECONNECT_WAIT = 2.0


@dataclass(slots=True)
class TelemetryConfig:
    """Runtime configuration for telemetry clients."""

    nats_url: str = field(default_factory=lambda: os.getenv("FOUNDRY_NATS_URL", _DEFAULT_NATS_URL))
    subject: str = field(default_factory=lambda: os.getenv("FOUNDRY_TELEMETRY_SUBJECT", _DEFAULT_SUBJECT))
    queue: str = field(default_factory=lambda: os.getenv("FOUNDRY_TELEMETRY_QUEUE", _DEFAULT_QUEUE))
    sink_path: Optional[Path] = field(default=None)
    connect_timeout: float = field(
        default_factory=lambda: float(os.getenv("FOUNDRY_NATS_CONNECT_TIMEOUT", _DEFAULT_CONNECT_TIMEOUT))
    )
    reconnect_time_wait: float = field(
        default_factory=lambda: float(os.getenv("FOUNDRY_NATS_RECONNECT_WAIT", _DEFAULT_RECONNECT_WAIT))
    )

    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        env_path = os.getenv("FOUNDRY_TELEMETRY_PATH")
        sink: Optional[Path]
        if env_path:
            sink = Path(env_path).expanduser()
            if not sink.is_absolute():
                sink = Path.cwd() / sink
        else:
            sink = Path.cwd() / _DEFAULT_SINK
        return cls(sink_path=sink)


def build_event(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a telemetry event dictionary."""

    return {
        "event": event_name,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def serialise_event(event: Dict[str, Any]) -> str:
    """Convert a telemetry event to a compact JSON string."""

    return json.dumps(event, default=_fallback_serializer, separators=(",", ":"))


class TelemetryJSONLSink:
    """Append-only JSONL sink for telemetry events."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = asyncio.Lock()

    async def write(self, event: Dict[str, Any]) -> None:
        """Append *event* to the JSONL sink."""

        line = serialise_event(event)

        async with self._lock:
            await asyncio.to_thread(self._write_line, line)

    def write_sync(self, event: Dict[str, Any]) -> None:
        """Synchronous helper primarily for tests and scripts."""

        line = serialise_event(event)
        self._write_line(line)

    def _write_line(self, line: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")


@dataclass(slots=True)
class TelemetryEvent:
    """Parsed telemetry message."""

    name: str
    payload: Dict[str, Any]
    timestamp: datetime
    raw: Dict[str, Any]

    @classmethod
    def from_message(cls, message: Msg) -> "TelemetryEvent":
        text = message.data.decode("utf-8", errors="replace")
        raw = json.loads(text)

        name = str(raw.get("event", ""))
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        timestamp = _parse_timestamp(raw.get("timestamp"))

        return cls(name=name, payload=payload, timestamp=timestamp, raw=raw)


class TelemetryPublisher:
    """Publish telemetry events to NATS, optionally mirroring to disk."""

    def __init__(
        self,
        config: Optional[TelemetryConfig] = None,
        *,
        mirror_sink: Optional[TelemetryJSONLSink] = None,
    ) -> None:
        self.config = config or TelemetryConfig.from_env()
        self._mirror = mirror_sink
        self._nats: Optional[NATS] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._nats and self._nats.is_connected:
            return

        async with self._lock:
            if self._nats and self._nats.is_connected:
                return

            client = NATS()
            await client.connect(
                servers=[self.config.nats_url],
                connect_timeout=self.config.connect_timeout,
                reconnect=True,
                max_reconnect_attempts=-1,
                reconnect_time_wait=self.config.reconnect_time_wait,
            )
            self._nats = client
            logger.info("Telemetry publisher connected to NATS %s", self.config.nats_url)

    async def publish(self, event_name: str, payload: Dict[str, Any]) -> None:
        event = build_event(event_name, payload)
        line = serialise_event(event).encode("utf-8")

        try:
            await self.connect()
            if self._nats:
                await self._nats.publish(self.config.subject, line)
        except Exception:
            logger.exception("failed_to_publish_telemetry event=%s", event_name)

        if self._mirror:
            try:
                await self._mirror.write(event)
            except Exception:
                logger.exception("failed_to_write_telemetry_mirror event=%s", event_name)

    async def close(self) -> None:
        if self._nats:
            try:
                await self._nats.drain()
            finally:
                self._nats = None
                logger.info("Telemetry publisher disconnected")


class TelemetrySubscriber:
    """Subscribe to telemetry subjects and dispatch to a handler."""

    def __init__(
        self,
        handler: Callable[[TelemetryEvent], Awaitable[None]],
        config: Optional[TelemetryConfig] = None,
    ) -> None:
        self.config = config or TelemetryConfig.from_env()
        self._handler = handler
        self._nats: Optional[NATS] = None

    async def connect(self) -> None:
        if self._nats and self._nats.is_connected:
            return

        client = NATS()
        await client.connect(
            servers=[self.config.nats_url],
            connect_timeout=self.config.connect_timeout,
            reconnect=True,
            max_reconnect_attempts=-1,
            reconnect_time_wait=self.config.reconnect_time_wait,
        )

        await client.subscribe(
            self.config.subject,
            queue=self.config.queue,
            cb=self._on_message,
        )

        self._nats = client
        logger.info(
            "Telemetry subscriber connected subject=%s queue=%s", self.config.subject, self.config.queue
        )

    async def close(self) -> None:
        if self._nats:
            try:
                await self._nats.drain()
            finally:
                self._nats = None
                logger.info("Telemetry subscriber disconnected")

    async def _on_message(self, msg: Msg) -> None:
        try:
            event = TelemetryEvent.from_message(msg)
        except Exception:
            logger.exception("failed_to_parse_telemetry_message")
            return

        try:
            await self._handler(event)
        except Exception:
            logger.exception("telemetry_handler_failed event=%s", event.name)


def _fallback_serializer(value: Any) -> str:
    return repr(value)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(timezone.utc)
