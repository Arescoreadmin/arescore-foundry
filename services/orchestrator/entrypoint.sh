#!/usr/bin/env sh
set -eu

# Ensure app.main:app exists
python - <<'PY' || { echo "Missing 'app' in app.main"; exit 90; }
import importlib
m = importlib.import_module("app.main")
assert hasattr(m, "app"), "Expected 'app' in app.main (FastAPI or Flask instance)"
PY

# Prefer FastAPI/uvicorn if available or install quickly if the app is FastAPI
if python - <<'PY'
import importlib, sys
m = importlib.import_module("app.main")
app = getattr(m, "app", None)
try:
    import fastapi; import uvicorn
    sys.exit(0)
except Exception:
    if app and app.__class__.__module__.startswith("fastapi"):
        sys.exit(2)  # fastapi app but missing libs
    sys.exit(1)
PY
then
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
elif [ "$?" -eq 2 ]; then
  pip install --no-cache-dir fastapi uvicorn >/dev/null 2>&1 || true
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
else
  # Try Flask; install if needed
  if python - <<'PY'
import importlib, sys
m = importlib.import_module("app.main")
app = getattr(m, "app", None)
try:
    import flask
    sys.exit(0)
except Exception:
    if app and app.__class__.__module__.startswith("flask"):
        sys.exit(2)
    sys.exit(1)
PY
  then
    exec python -m flask --app app.main run --host 0.0.0.0 --port 8080
  elif [ "$?" -eq 2 ]; then
    pip install --no-cache-dir flask >/dev/null 2>&1 || true
    exec python -m flask --app app.main run --host 0.0.0.0 --port 8080
  else
    exec python -m app.main
  fi
fi
