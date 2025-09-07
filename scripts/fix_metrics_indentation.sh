#!/usr/bin/env bash
set -Eeuo pipefail

ORCH_SVC="orchestrator"
BASE_COMPOSE="infra/docker-compose.yml"
OVERRIDES=()
[[ -f infra/docker-compose.hardening.override.yml ]] && OVERRIDES+=(-f infra/docker-compose.hardening.override.yml)
[[ -f infra/docker-compose.frontend-tmpfs.override.yml ]] && OVERRIDES+=(-f infra/docker-compose.frontend-tmpfs.override.yml)

MAIN_PY="${MAIN_PY:-backend/orchestrator/app/main.py}"
REQS_FILE="${REQS_FILE:-backend/orchestrator/requirements.txt}"
BEGIN_M='# --- BEGIN auto metrics wiring'
END_M='# --- END auto metrics wiring'

say(){ printf "\033[1;36m==>\033[0m %s\n" "$*"; }
die(){ printf "\033[1;31mERROR:\033[0m %s\n" "$*" >&2; exit 1; }

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

[[ -f "$MAIN_PY" ]] || die "main.py not found at $MAIN_PY (set MAIN_PY=…)."
[[ -f "$REQS_FILE" ]] || die "requirements.txt not found at $REQS_FILE."

# 1) Backup
TS="$(date +%Y%m%d-%H%M%S)"
cp -f "$MAIN_PY" "$MAIN_PY.bak.$TS"

# 2) Normalize line endings + tabs -> spaces
say "Normalizing line endings and indentation…"
awk '{sub(/\r$/,""); print}' "$MAIN_PY" > "$MAIN_PY.tmp.$$"
mv "$MAIN_PY.tmp.$$" "$MAIN_PY"
# Replace tabs with 4 spaces
sed -i 's/\t/    /g' "$MAIN_PY"

# 3) Remove any old managed block completely
if grep -q "$BEGIN_M" "$MAIN_PY"; then
  say "Removing previous managed metrics block…"
  awk -v b="$BEGIN_M" -v e="$END_M" '
    BEGIN{skip=0}
    index($0,b){skip=1; next}
    index($0,e){skip=0; next}
    skip==0{print}
  ' "$MAIN_PY" > "$MAIN_PY.tmp" && mv "$MAIN_PY.tmp" "$MAIN_PY"
fi

# 4) Comment any one-liner expose wiring (keep code, avoid double instrumentation)
say "Neutralizing stray Instrumentator expose lines…"
sed -i -E 's/^(\s*from\s+prometheus_fastapi_instrumentator.*)$/# \1/' "$MAIN_PY" || true
sed -i -E 's/^(\s*import\s+prometheus_fastapi_instrumentator.*)$/# \1/' "$MAIN_PY" || true
sed -i -E 's/(Instrumentator\(.*\)\.instrument\(app\)\.expose\(app.*)/# \1/' "$MAIN_PY" || true

# 5) Append a clean, strictly-spaced block at module top-level
say "Injecting clean metrics block…"
cat >>"$MAIN_PY" <<'PYBLOCK'

# --- BEGIN auto metrics wiring (do not edit) ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instr

    _EXCLUDE = {"/metrics", "/health", "/_healthz", "/readyz"}
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

# 6) Compile check (host Python) — catches indentation/syntax before rebuild
say "Local compile check…"
python - <<PY
import py_compile, sys
try:
    py_compile.compile("$MAIN_PY", doraise=True)
except Exception as e:
    print(e)
    sys.exit(1)
PY

# 7) Ensure dependency present
if ! grep -qiE '^prometheus-fastapi-instrumentator(\b|==|>=|~=)' "$REQS_FILE"; then
  say "Adding prometheus-fastapi-instrumentator to $REQS_FILE"
  printf '\nprometheus-fastapi-instrumentator>=6.1.0\n' >> "$REQS_FILE"
fi

# 8) Rebuild + restart + health gate
say "Rebuilding API image…"
docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" build "$ORCH_SVC" >/dev/null
say "Restarting API…"
docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" up -d "$ORCH_SVC" >/dev/null

CID="$(docker compose -f "$BASE_COMPOSE" "${OVERRIDES[@]}" ps -q "$ORCH_SVC")"
[[ -n "$CID" ]] || die "No container for $ORCH_SVC."

say "Waiting for healthy…"
for i in {1..60}; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo starting)"
  [[ "$state" == "healthy" ]] && { say "healthy ✅"; break; }
  [[ "$state" == "unhealthy" ]] && { docker logs --tail=200 "$CID" || true; die "Container unhealthy."; }
  sleep 5
  [[ $i -eq 60 ]] && die "Timed out waiting for healthy (state=$state)"
done

# 9) Verify /metrics and exclusions
say "Verifying /metrics is 200…"
[[ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/metrics)" == "200" ]] || die "/metrics not 200"

say "Ensuring health endpoints are excluded from request metrics…"
if curl -s http://127.0.0.1:8000/metrics \
  | grep -E '^(http_requests_total|http_request_duration_seconds).*handler="/(_healthz|health|readyz)"' >/dev/null; then
  die "Health endpoints still present in request metrics"
else
  echo "✅ Health endpoints excluded."
fi

say "Done."
