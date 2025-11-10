from __future__ import annotations

from pathlib import Path

import pytest

from backend.orchestrator.app.schemas import Topology
from backend.orchestrator.app.state import SessionState, SessionStore


TOPOLOGY = Topology.from_yaml(
    """
    name: state
    containers:
      - name: only
        image: alpine
    """
)


def test_state_transitions(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    session = store.create_session(identifier="abc", name="demo", topology=TOPOLOGY)
    assert session.state == SessionState.PENDING

    session = store.transition("abc", SessionState.SPAWNING)
    assert session.state == SessionState.SPAWNING

    session = store.transition("abc", SessionState.ACTIVE)
    assert session.state == SessionState.ACTIVE

    session = store.transition("abc", SessionState.COMPLETED)
    assert session.state == SessionState.COMPLETED


def test_illegal_transition(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions.json")
    store.create_session(identifier="abc", name="demo", topology=TOPOLOGY)
    with pytest.raises(ValueError):
        store.transition("abc", SessionState.COMPLETED)
