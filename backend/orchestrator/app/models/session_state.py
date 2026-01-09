"""Session state machine with filesystem persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from .schemas import Topology


class SessionState(str, Enum):
    PENDING = "pending"
    SPAWNING = "spawning"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


ALLOWED_TRANSITIONS = {
    SessionState.PENDING: {SessionState.SPAWNING, SessionState.FAILED},
    SessionState.SPAWNING: {SessionState.ACTIVE, SessionState.FAILED},
    SessionState.ACTIVE: {SessionState.COMPLETED, SessionState.FAILED},
}


class SessionRecord(BaseModel):
    id: str
    name: str
    topology: Topology
    state: SessionState = SessionState.PENDING
    history: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(use_enum_values=True)


class SessionStore:
    """Filesystem backed session persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._sessions: Dict[str, SessionRecord] = {}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        payload = json.loads(self._path.read_text())
        self._sessions = {
            identifier: SessionRecord.model_validate(data) for identifier, data in payload.items()
        }

    def _persist(self) -> None:
        serialised = {identifier: record.model_dump() for identifier, record in self._sessions.items()}
        self._path.write_text(json.dumps(serialised, default=str, indent=2))

    def create_session(self, *, identifier: str, name: str, topology: Topology) -> SessionRecord:
        with self._lock:
            if identifier in self._sessions:
                raise ValueError(f"Session '{identifier}' already exists")
            record = SessionRecord(id=identifier, name=name, topology=topology)
            record.history.append(self._history_entry(SessionState.PENDING))
            self._sessions[identifier] = record
            self._persist()
            return record

    def transition(self, identifier: str, target: SessionState, detail: str | None = None) -> SessionRecord:
        with self._lock:
            record = self._get(identifier)
            if record.state == target:
                return record
            allowed = ALLOWED_TRANSITIONS.get(record.state, set())
            if target not in allowed:
                raise ValueError(f"Illegal transition from {record.state} to {target}")
            record.state = target
            record.updated_at = datetime.now(timezone.utc)
            record.history.append(self._history_entry(target, detail))
            self._persist()
            return record

    def set_state(self, identifier: str, target: SessionState, detail: str | None = None) -> SessionRecord:
        with self._lock:
            record = self._get(identifier)
            record.state = target
            record.updated_at = datetime.now(timezone.utc)
            record.history.append(self._history_entry(target, detail))
            self._persist()
            return record

    def get(self, identifier: str) -> SessionRecord:
        with self._lock:
            return self._get(identifier)

    def _get(self, identifier: str) -> SessionRecord:
        try:
            return self._sessions[identifier]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown session '{identifier}'") from exc

    def list(self) -> List[SessionRecord]:
        with self._lock:
            return sorted(self._sessions.values(), key=lambda record: record.created_at)

    def _history_entry(self, state: SessionState, detail: str | None = None) -> dict:
        return {
            "state": state.value,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


__all__ = ["SessionState", "SessionStore", "SessionRecord"]
