#!/usr/bin/env python
from __future__ import annotations

<<<<<<< HEAD
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '[audit_report] %s\n' "$1"
}

AUDIT_FILE="${FOUNDRY_TELEMETRY_PATH:-$ROOT_DIR/audits/foundry-events.jsonl}"
DEFAULT_PARQUET="${AUDIT_FILE%.jsonl}.parquet"
if [[ "$DEFAULT_PARQUET" == "$AUDIT_FILE" ]]; then
  DEFAULT_PARQUET="${AUDIT_FILE}.parquet"
fi
PARQUET_FILE="${AUDIT_PARQUET_PATH:-$DEFAULT_PARQUET}"

if [[ ! -f "$AUDIT_FILE" ]]; then
  log "Audit file not found at $AUDIT_FILE"
  exit 1
fi

PYTHON_BIN=${PYTHON:-python3}
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  else
    log "Python interpreter not found (set PYTHON env var if using a venv)."
    exit 1
  fi
fi

log "Summary from $(basename "$AUDIT_FILE")"
"$PYTHON_BIN" "$ROOT_DIR/scripts/audit_report.py" --path "$AUDIT_FILE"

run_duckdb() {
  if command -v duckdb >/dev/null 2>&1; then
    duckdb "$@"
    return
  fi

  if ! command -v docker >/dev/null 2>&1; then
    log "DuckDB CLI not available and docker is missing; cannot continue."
    exit 1
  fi

  if docker compose version >/dev/null 2>&1; then
    docker compose run --rm duckdb "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose run --rm duckdb "$@"
  else
    log "Neither 'docker compose' nor 'docker-compose' available."
    exit 1
  fi
}

log "Event counts by type (DuckDB):"
EVENT_SQL=$(cat <<SQL
COPY (
  SELECT event, COUNT(*) AS count
  FROM read_json_auto('$AUDIT_FILE', format='jsonl')
  GROUP BY event
  ORDER BY count DESC
) TO STDOUT (FORMAT CSV, HEADER);
SQL
)
run_duckdb -c "$EVENT_SQL"

log "Writing Parquet export to ${PARQUET_FILE}"
PARQUET_SQL=$(cat <<SQL
COPY (
  SELECT *
  FROM read_json_auto('$AUDIT_FILE', format='jsonl')
) TO '$PARQUET_FILE' (FORMAT PARQUET);
SQL
)
run_duckdb -c "$PARQUET_SQL"

log "Done."
=======
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def load_events(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Audit file not found: {path}")

    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # best-effort; don't blow up on a bad line
                continue
    return events


def parse_ts(ev: Dict[str, Any]) -> datetime | None:
    ts = ev.get("timestamp")
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def summarize(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "No events found."

    by_kind = Counter()
    by_template = Counter()
    scenario_ids: set[str] = set()

    for ev in events:
        kind = ev.get("event") or ev.get("kind") or "unknown"
        by_kind[kind] += 1

        payload = ev.get("payload") or {}
        if isinstance(payload, dict):
            tmpl = payload.get("template")
            sid = payload.get("scenario_id")
            if isinstance(tmpl, str):
                by_template[tmpl] += 1
            if isinstance(sid, str):
                scenario_ids.add(sid)

    timestamps = [ts for ts in (parse_ts(e) for e in events) if ts is not None]
    newest_ts = max(timestamps) if timestamps else None
    newest_ts_str = newest_ts.isoformat() if newest_ts else "unknown"

    lines: List[str] = []
    lines.append(f"Total events: {len(events)}")
    lines.append(f"Unique scenarios (by scenario_id): {len(scenario_ids)}")
    lines.append(f"Most recent event timestamp: {newest_ts_str}")
    lines.append("")
    lines.append("Events by kind:")
    for kind, count in by_kind.most_common():
        lines.append(f"  {kind}: {count}")

    if by_template:
        lines.append("")
        lines.append("scenario.created by template:")
        for tmpl, count in by_template.most_common():
            lines.append(f"  {tmpl}: {count}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Foundry audit events.")
    parser.add_argument(
        "--path",
        "-p",
        default=None,
        help="Path to JSONL audit file (default: $FOUNDRY_TELEMETRY_PATH or audits/foundry-events.jsonl)",
    )
    args = parser.parse_args()

    env_path = Path(
        (  # type: ignore[arg-type]
            __import__("os").environ.get("FOUNDRY_TELEMETRY_PATH", "audits/foundry-events.jsonl")
        )
    )
    path = Path(args.path) if args.path else env_path

    events = load_events(path)
    print(summarize(events))


if __name__ == "__main__":
    main()
>>>>>>> origin/main
