import json
from pathlib import Path

import pytest

from services.common.telemetry import TelemetryJSONLSink, build_event


@pytest.fixture(autouse=True)
def cleanup_env(monkeypatch):
    monkeypatch.delenv("FOUNDRY_TELEMETRY_PATH", raising=False)


def _read_events(path: Path) -> list[dict]:
    contents = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in contents if line]


def test_sink_writes_json_line(tmp_path):
    sink_path = tmp_path / "audits" / "foundry-events.jsonl"
    sink = TelemetryJSONLSink(sink_path)

    sink.write_sync(build_event("scenario.created", {"scenario_id": "abc-123"}))

    events = _read_events(sink_path)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "scenario.created"
    assert event["payload"] == {"scenario_id": "abc-123"}
    assert event["timestamp"].endswith("+00:00")


def test_sink_serialises_unknown_types(tmp_path):
    sink_path = tmp_path / "audits" / "foundry-events.jsonl"

    class Custom:
        def __repr__(self) -> str:  # pragma: no cover - exercised indirectly
            return "<Custom>"

    sink = TelemetryJSONLSink(sink_path)
    sink.write_sync(build_event("custom", {"obj": Custom()}))

    event = _read_events(sink_path)[0]
    assert event["payload"] == {"obj": "<Custom>"}
