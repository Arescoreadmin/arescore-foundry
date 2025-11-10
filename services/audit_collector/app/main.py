from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from services.common.telemetry import (
    TelemetryConfig,
    TelemetryEvent,
    TelemetryJSONLSink,
    TelemetrySubscriber,
)

logger = logging.getLogger(__name__)


async def _run_collector() -> None:
    config = TelemetryConfig.from_env()
    sink_path = config.sink_path or Path.cwd() / "audits" / "foundry-events.jsonl"
    sink = TelemetryJSONLSink(sink_path)

    async def handle(event: TelemetryEvent) -> None:
        await sink.write(event.raw)
        logger.debug("wrote_telemetry_event event=%s", event.name)

    subscriber = TelemetrySubscriber(handler=handle, config=config)
    await subscriber.connect()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # pragma: no cover - Windows compatibility
            pass

    logger.info(
        "audit_collector ready nats_url=%s subject=%s sink=%s",
        config.nats_url,
        config.subject,
        sink_path,
    )

    try:
        await stop_event.wait()
    finally:
        await subscriber.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")

    try:
        asyncio.run(_run_collector())
    except KeyboardInterrupt:  # pragma: no cover - interactive use
        logger.info("audit_collector shutdown via KeyboardInterrupt")


if __name__ == "__main__":
    main()
