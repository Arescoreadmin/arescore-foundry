#!/usr/bin/env bash
set -Eeuo pipefail

# --- config ----------------------------------------------------
ORCH_SVC="orchestrator"
BASE_COMPOSE="infra/docker-compose.yml"
OVERRIDES=()
[[ -f "infra/docker-compose.hardening.override.yml" ]] && OVERRIDES+=("-f" "infra/docker-compose.hardening.override.yml")
[[ -f "infra/docker-compose.frontend-tmpfs.override.yml" ]] && OVERRIDES+=("-f" "infra/docker-compose.frontend-tmpfs.override.yml")

MAIN_PY_DEFAULT="backend/orchestrator/app/main.py"
REQS_DEFAULT="backend/orchestrator/requirements.txt"

# Allow overrides via env
MAIN_PY="${MAIN_PY:-$MAIN_PY_DEFAULT}"
REQS_FILE="${REQS_FILE:-$REQS_DEFAULT}"
# ---------------------------------------------------------------

say() { printf "\033[1;36m==>\033[0m %s\n" "$*"; }
die() { printf "\033[1;31mERROR:\033[0m %s\n" "$*" >&2; exit 1; }

# Find repo root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Try to auto-detect main.py if the default isn't there
if [[ ! -f "$MAIN_PY" ]]; then
  cand="$(grep -RIl --include='main.py' -E 'FastAPI\(' backend 2>/dev/null | grep orchestrator | head -n1 || true)"
  [[ -z "$cand" ]] && cand="$(grep -RIl --include='main.py' -E 'FastAPI\(' backend 2>/dev/null | head -n1 || true)"
  [[ -n "$cand" ]] && MAIN_PY="$cand"
fi
[[ -f "$MAIN_PY" ]] || die "Cannot find FastAPI main.py (looked at $MAIN_PY). Set MAIN_PY=… and retry."

say "Target main.py: $MAIN_PY"

# Ensure dependency in requirements
if [[ -f "$REQS_FILE" ]]; then
  if ! grep -qiE '^prometheus-fastapi-instrumentator(\b|==|>=|~=)' "$REQS_FILE"; then
    say "Adding prometheus-fastapi-instrumentator to $REQS_FILE"
    printf '\nprometheus-fastapi-instrumentator>=6.1.0\n' >> "$REQS_FILE"
  else
    say "Dependency already present in $REQS_FILE"
  fi
else
  die "Requirements file not found at $REQS_FILE (set REQS_FILE=… if needed)."
fi

# Backup file (once per run)
cp -f "$MAIN_PY" "$MAIN_PY.bak.$(date +%Y%m%d-%H%M%S)"

# Comment out simple, common one-liners of previous wiring to avoid double instrumentation
# (Non-destructive; we’ll also enforce our block below.)
say "Neutralizing any previous Instrumentator expose calls (if present)…"
sed -i -E 's/^(\s*from\s+prometheus_fastapi_instrumentator.*)$/# \1/' "$MAIN_PY" || true
sed -i -E 's/^(\s*import\s+prometheus_fastapi_instrumentator.*)$/# \1/' "$MAIN_PY" || true
sed -i -E 's/^(.*Instrumentator\(.*\)\.instrument\(app\)\.expose\(app.*)$/# \1/' "$MAIN_PY" || true

# Replace our managed block if already present; otherwise append.
BEGIN_RE='# --- BEGIN auto metrics wiring'
END_RE='# --- END auto metrics wiring'

if grep -q "$BEGIN_RE" "$MAIN_PY"; then
  say "Refreshing existing managed metrics block…"
  awk -v b="$BEGIN_RE" -v e="$END_RE" '
    BEGIN{inblk=0}
    index($0,b){print b; inblk=1; next}
    index($0,e){print e; inblk=0; skip=1; next}
    inblk==0{print}
  ' "$MAIN_PY" > "$MAIN_PY.tmp"
  mv "$MAIN_PY.tmp" "$MAIN_PY"
fi

say "Injecting idempotent metrics wiring…"
cat >>"$MAIN_PY" <<'PYBLOCK'

# --- BEGIN auto metrics wiring (do not edit) ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instr

    _EXCLUDE = {"/metrics", "/health", "/_healthz", "/readyz"}
    # Avoid double-exposing if already present (e.g., reloader)
    _already = any(getattr(r, "path", "") == "/metrics" for r in getattr(app, "routes", []))

    if not _already:
        _instr = _Instr(
            excluded_handlers=[r"^/metrics$", r"^/health$", r"^/_healthz$", r"^/readyz$"],
            should_ignore=lambda req: getattr(req, "url", None)
            and getattr(req.url, "path", "") in _EXCLUDE,
        )
        _instr.instrument(app).expose(app, include_in_schema=False)
except Exception:
    # Never block startup if metrics wiring fails
    pass
# --- END auto metrics wiring ---
PYBLOCK

# Rebuild and restart orchestrator
say "Rebuilding API image…"
docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" build "$ORCH_SVC" >/dev/null

say "Restarting API container…"
docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" up -d "$ORCH_SVC" >/dev/null

# Wait for healthy (up to ~5 minutes)
CID="$(docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" ps -q "$ORCH_SVC")"
[[ -n "$CID" ]] || die "Could not find container ID for $ORCH_SVC."

say "Waiting for healthy…"
attempts=0; max_attempts=60
while :; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo starting)"
  [[ "$state" == "healthy" ]] && { say "healthy ✅"; break; }
  [[ "$state" == "unhealthy" ]] && { docker logs --tail=200 "$CID" || true; die "Container unhealthy."; }
  ((attempts+=1))
  (( attempts >= max_attempts )) && { docker logs --tail=200 "$CID" || true; die "Timed out waiting for healthy (state=$state)"; }
  sleep 5
done

# Verify /metrics is up
say "Verifying /metrics endpoint…"
code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/metrics || true)"
if [[ "$code" != "200" ]]; then
  die "/metrics returned HTTP $code — instrumentation not exposed."
fi

# Verify health endpoints are excluded from request metrics
say "Ensuring health endpoints are excluded from request metrics…"
if curl -s http://127.0.0.1:8000/metrics \
   | grep -E '^(http_requests_total|http_request_duration_seconds).*handler="/(_healthz|health|readyz)"' >/dev/null; then
  echo "Found health endpoints in request metrics:"
  curl -s http://127.0.0.1:8000/metrics \
   | grep -E '^(http_requests_total|http_request_duration_seconds).*handler="/(_healthz|health|readyz)"'
  die "Exclusion failed — please inspect $MAIN_PY."
else
  echo "✅ Health endpoints excluded from request metrics."
fi

# Sanity: core metrics still present
if ! curl -s http://127.0.0.1:8000/metrics | grep -q '^python_gc_objects_collected_total'; then
  die "Base Python metrics not found — something’s off."
fi

say "All good. Metrics exposed at /metrics, health endpoints excluded."
