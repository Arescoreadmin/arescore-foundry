from __future__ import annotations

import asyncio

from backend.orchestrator.app.messaging import InMemoryEventBus, SpawnEvent, StatusUpdate


def test_in_memory_bus_dispatches_handlers() -> None:
    bus = InMemoryEventBus()
    updates: list[str] = []

    async def handler(update: StatusUpdate) -> None:
        updates.append(update.state)

    async def scenario() -> None:
        await bus.start()
        await bus.subscribe_to_status(handler)
        await bus.publish_status_update(StatusUpdate(session_id="1", state="active"))
        await bus.publish_spawn_event(SpawnEvent(session_id="1", topology_name="demo", plan={}))

    asyncio.run(scenario())

    assert updates == ["active"]
    assert bus.spawn_events
