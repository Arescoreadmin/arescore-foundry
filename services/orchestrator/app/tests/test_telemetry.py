import json
from pathlib import Path

import pytest

from ..telemetry import emit_event


@pytest.fixture(autouse=True)
def cleanup_env(monkeypatch):
    monkeypatch.delenv("FOUNDRY_TELEMETRY_PATH", raising=False)


def _read_events(path: Path) -> list[dict]:
    contents = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in contents if line]


def test_emit_event_writes_json_line(tmp_path, monkeypatch):
    sink = tmp_path / "audits" / "foundry-events.jsonl"
    monkeypatch.setenv("FOUNDRY_TELEMETRY_PATH", str(sink))

    emit_event("scenario.created", {"scenario_id": "abc-123"})

    events = _read_events(sink)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "scenario.created"
    assert event["payload"] == {"scenario_id": "abc-123"}
    assert event["timestamp"].endswith("+00:00")


def test_emit_event_serialises_unknown_types(tmp_path, monkeypatch):
    sink = tmp_path / "audits" / "foundry-events.jsonl"
    monkeypatch.setenv("FOUNDRY_TELEMETRY_PATH", str(sink))

    class Custom:
        def __repr__(self) -> str:  # pragma: no cover - exercised indirectly
            return "<Custom>"

    emit_event("custom", {"obj": Custom()})

    event = _read_events(sink)[0]
    assert event["payload"] == {"obj": "<Custom>"}
