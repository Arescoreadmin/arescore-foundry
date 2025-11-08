#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON="${PYTHON:-"$ROOT_DIR/.venv/bin/python"}"
AUDIT_FILE="${FOUNDRY_TELEMETRY_PATH:-"$ROOT_DIR/audits/foundry-events.jsonl"}"

if [[ ! -x "$PYTHON" ]]; then
  echo "[audit_report] Python not found at $PYTHON" >&2
  exit 1
fi

if [[ ! -f "$AUDIT_FILE" ]]; then
  echo "[audit_report] Audit file not found at $AUDIT_FILE" >&2
  exit 1
fi

exec "$PYTHON" "$ROOT_DIR/scripts/audit_report.py" --path "$AUDIT_FILE"
