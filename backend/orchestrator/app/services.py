"""Domain services orchestrating topology sessions."""

from __future__ import annotations

import uuid
from typing import Tuple

from .messaging import EventBus, SpawnEvent, StatusUpdate
from .schemas import Topology
from .state import SessionRecord, SessionState, SessionStore
from .translator import DockerPlan, TopologyTranslator


class SessionService:
    """High level orchestration for session lifecycle management."""

    def __init__(
        self,
        *,
        store: SessionStore,
        translator: TopologyTranslator,
        event_bus: EventBus,
    ) -> None:
        self._store = store
        self._translator = translator
        self._event_bus = event_bus

    async def create_session(self, *, name: str, topology: Topology) -> Tuple[SessionRecord, DockerPlan]:
        identifier = str(uuid.uuid4())
        record = self._store.create_session(identifier=identifier, name=name, topology=topology)
        plan = self._translator.translate(topology)
        record = self._store.transition(identifier, SessionState.SPAWNING, detail="Session queued for spawn")
        await self._event_bus.publish_spawn_event(
            SpawnEvent(session_id=identifier, topology_name=topology.name, plan=plan.model_dump())
        )
        return record, plan

    async def handle_status_update(self, update: StatusUpdate) -> None:
        state = SessionState(update.state)
        if state in {SessionState.ACTIVE, SessionState.COMPLETED, SessionState.FAILED}:
            self._store.set_state(update.session_id, state, detail=update.detail)
        elif state == SessionState.SPAWNING:
            self._store.transition(update.session_id, SessionState.SPAWNING, detail=update.detail)
        else:
            self._store.set_state(update.session_id, state, detail=update.detail)

    async def publish_status(self, identifier: str, state: SessionState, detail: str | None = None) -> None:
        await self._event_bus.publish_status_update(
            StatusUpdate(session_id=identifier, state=state.value, detail=detail)
        )

    def list_sessions(self) -> list[SessionRecord]:
        return self._store.list()

    def get_session(self, identifier: str) -> SessionRecord:
        return self._store.get(identifier)


__all__ = ["SessionService"]
