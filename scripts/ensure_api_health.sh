#!/usr/bin/env bash
set -Eeuo pipefail

ORCH_SVC="orchestrator"
BASE_COMPOSE="infra/docker-compose.yml"
OVERRIDE_COMPOSE="infra/docker-compose.health.override.yml"

echo "==> Locating FastAPI main.py…"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Optional: point directly at a main.py with MAIN_PY=…
if [[ -n "${MAIN_PY:-}" ]]; then
  CANDIDATE="$MAIN_PY"
else
  CANDIDATE="$(grep -RIl --include='main.py' -E 'FastAPI\(' backend 2>/dev/null | head -n1 || true)"
fi

if [[ -n "${CANDIDATE:-}" && -f "$CANDIDATE" ]]; then
  echo "==> Found: $CANDIDATE"
  # Best-effort: add /_healthz alias only if clearly missing
  if ! grep -qE '/_healthz' "$CANDIDATE"; then
    echo "==> Injecting /_healthz alias into $CANDIDATE"
    cat >>"$CANDIDATE" <<'PYADD'

# --- BEGIN: injected health alias (do not remove) ---
try:
    _paths = [getattr(r, "path", "") for r in getattr(app, "routes", [])]
except Exception:
    _paths = []
if "/_healthz" not in _paths:
    try:
        app.add_api_route("/_healthz", health, include_in_schema=False)
    except Exception:
        @app.get("/_healthz", include_in_schema=False)
        def _healthz():
            return {"status": "ok"}
# --- END: injected health alias ---
PYADD
  else
    echo "==> /_healthz already present — skipping injection."
  fi
else
  echo "==> No main.py found (that’s OK)."
fi

echo "==> Writing $OVERRIDE_COMPOSE"
cat >"$OVERRIDE_COMPOSE" <<YAML
services:
  orchestrator:
    healthcheck:
      test:
        - "CMD"
        - "python3"
        - "-c"
        - |
          import sys, socket, urllib.request
          socket.setdefaulttimeout(2)
          for path in ("/_healthz", "/health"):
              url = f"http://127.0.0.1:8000{path}"
              try:
                  r = urllib.request.urlopen(url)
                  code = getattr(r, "status", getattr(r, "code", 200))
                  if 200 <= code < 400:
                      sys.exit(0)
              except Exception:
                  pass
          sys.exit(1)
      interval: 5s
      timeout: 3s
      start_period: 10s
      retries: 12
YAML

echo "==> Rebuilding orchestrator with override…"
docker compose -f "$BASE_COMPOSE" -f "$OVERRIDE_COMPOSE" build "$ORCH_SVC"

echo "==> Restarting orchestrator…"
docker compose -f "$BASE_COMPOSE" -f "$OVERRIDE_COMPOSE" up -d "$ORCH_SVC"

echo "==> Waiting for healthy…"
CID="$(docker compose -f "$BASE_COMPOSE" -f "$OVERRIDE_COMPOSE" ps -q "$ORCH_SVC")"
attempts=0; max_attempts=60
while true; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
  if [[ "$state" == "healthy" ]]; then
    echo "==> Healthy ✅"
    break
  fi
  if [[ "$state" == "unhealthy" ]]; then
    echo "==> UNHEALTHY ❌ — last health logs:"; docker inspect "$CID" --format '{{range .State.Health.Log}}{{println .Output}}{{end}}' | tail -n 10 || true
    exit 1
  fi
  ((attempts+=1))
  (( attempts >= max_attempts )) && { echo "==> Timeout waiting for healthy (state=$state)"; docker logs --tail=200 "$CID" || true; exit 1; }
  printf "   [%02d] state=%s\n" "$attempts" "$state"
  sleep 5
done

echo "==> Verifying endpoints…"
if command -v curl >/dev/null 2>&1; then
  echo -n "GET /health: " && curl -fsS "http://127.0.0.1:8000/health" || true; echo
  echo -n "GET /_healthz: " && curl -fsS "http://127.0.0.1:8000/_healthz" || true; echo
fi

echo "==> Done."
