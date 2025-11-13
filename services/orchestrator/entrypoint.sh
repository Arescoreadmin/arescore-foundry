#!/usr/bin/env sh
set -eu

python - <<'PY' || exit 90
import importlib
m = importlib.import_module("app.main")
assert hasattr(m, "app"), "Expected 'app' in app.main (FastAPI instance)"
PY

UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
UVICORN_PORT="${UVICORN_PORT:-8080}"

exec python -m uvicorn app.main:app --host "$UVICORN_HOST" --port "$UVICORN_PORT"
