#!/usr/bin/env bash
set -euo pipefail

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
