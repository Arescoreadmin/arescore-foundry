#!/usr/bin/env sh
set -eu

python - <<'PY' || exit 90
import importlib
m = importlib.import_module("app.main")
assert hasattr(m, "app"), "Expected 'app' in app.main (FastAPI instance)"
PY

DEFAULT_HOST="0.0.0.0"
UVICORN_HOST="${UVICORN_HOST:-$DEFAULT_HOST}"
UVICORN_PORT="${UVICORN_PORT:-8080}"

case "$UVICORN_HOST" in
  "127.0.0.1"|"localhost"|"::1")
    echo "[entrypoint] overriding loopback UVICORN_HOST=$UVICORN_HOST to $DEFAULT_HOST for container reachability" >&2
    UVICORN_HOST="$DEFAULT_HOST"
    ;;
esac

exec python -m uvicorn app.main:app --host "$UVICORN_HOST" --port "$UVICORN_PORT"
