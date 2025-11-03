#!/usr/bin/env sh
set -eu
python - <<'PY' || exit 90
import importlib
m = importlib.import_module("app.main")
assert hasattr(m, "app"), "Expected 'app' in app.main (FastAPI instance)"
PY
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
