# scripts/smoke_overlay.sh
#!/usr/bin/env bash
set -euo pipefail

COMPOSE="docker compose --profile control-plane --profile range-plane -f compose.yml -f compose.federated.yml"
CURL="curl -fsS --max-time 3"

RETRIES=${RETRIES:-40}
SLEEP=${SLEEP:-1}

say() { printf '%b\n' "$*"; }
ok()  { say "OK: $*"; }
err() { say "FAIL: $*"; }

# --- 0) Gate on OPA unit tests
say "==> OPA unit tests"
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:1.10.0 test /policies -v >/dev/null
ok "OPA tests passed"

# --- 1) Ensure stack is up
say "==> Ensuring stack is up (compose + federated)"
$COMPOSE up -d --remove-orphans >/dev/null
$COMPOSE ps

# --- 2) Wait for container health (robust via docker inspect)
say "==> Waiting for containers to be healthy"
need_healthy=(opa nats minio loki orchestrator ingestors fl_coordinator consent_registry evidence_bundler)

health_of() {
  local svc="$1"
  local cid="$($COMPOSE ps -q "$svc" 2>/dev/null | head -n1)"
  [ -z "$cid" ] && { echo "missing"; return; }
  local has_hc
  has_hc="$(docker inspect -f '{{if .State.Health}}yes{{end}}' "$cid" 2>/dev/null || true)"
  if [ "$has_hc" = "yes" ]; then
    docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "unknown"
  else
    docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown"
  fi
}

for svc in "${need_healthy[@]}"; do
  i=0
  while :; do
    status="$(health_of "$svc")"
    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
      ok "$svc healthy"
      break
    fi
    i=$((i+1))
    if [ $i -ge $RETRIES ]; then
      err "$svc did not become healthy (last status: $status)"
      $COMPOSE logs --tail=80 "$svc" || true
      exit 1
    fi
    sleep "$SLEEP"
  done
done

# --- 3) HTTP probe helpers with retries
wait_http() {
  local method="$1" url="$2" body="${3:-}"
  local i=0
  while :; do
    if [ "$method" = "GET" ]; then
      if $CURL "$url" >/dev/null 2>&1; then return 0; fi
    else
      if printf '%s' "$body" | $CURL -X "$method" -d @- "$url" >/dev/null 2>&1; then return 0; fi
    fi
    i=$((i+1)); [ $i -ge $RETRIES ] && return 1
    sleep "$SLEEP"
  done
}

say "==> Service health checks"
declare -A checks=(
  ["fl_coordinator (GET /health)"]="GET http://127.0.0.1:9092/health"
  ["consent_opt_in (POST /consent/training/optin)"]="POST http://127.0.0.1:9093/consent/training/optin"
  ["consent_crl (GET /crl)"]="GET http://127.0.0.1:9093/crl"
  ["evidence_bundler (GET /health)"]="GET http://127.0.0.1:9094/health"
  ["orchestrator (GET /health)"]="GET http://127.0.0.1:8080/health"
  ["ingestors (GET /health)"]="GET http://127.0.0.1:8070/health"
)

fail=0
for label in "${!checks[@]}"; do
  read -r method url <<<"${checks[$label]}"
  if wait_http "$method" "$url"; then
    ok "$label"
  else
    err "$label (URL: $url)"
    fail=1
  fi
done

[ $fail -eq 0 ] && { say "All green."; exit 0; } || { say "One or more checks failed."; exit 1; }
