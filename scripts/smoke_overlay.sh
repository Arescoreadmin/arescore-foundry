#!/usr/bin/env bash
set -euo pipefail

trap 'echo "Smoke test failed at $(date)" >&2' ERR

# -----------------------------
# Config
# -----------------------------

# Allow overrides from CI or local env
COMPOSE_PROFILES="${COMPOSE_PROFILES:-control-plane,range-plane}"
COMPOSE_FILES="${COMPOSE_FILES:-compose.yml,compose.federated.yml}"

# Turn comma-separated into repeated -f / --profile flags
build_compose_cmd() {
  local files profiles
  IFS=',' read -r -a files <<<"$COMPOSE_FILES"
  IFS=',' read -r -a profiles <<<"$COMPOSE_PROFILES"

  local args=()
  for f in "${files[@]}"; do
    args+=(-f "$f")
  done
  for p in "${profiles[@]}"; do
    args+=(--profile "$p")
  done

  printf 'docker compose %s' "${args[*]}"
}

COMPOSE="$(build_compose_cmd)"
CURL="curl -fsS --max-time 3"

# How long we wait for containers / HTTP checks
RETRIES=${RETRIES:-60}
SLEEP=${SLEEP:-1}

say() { printf '%b\n' "$*"; }
ok()  { say "OK: $*"; }
err() { say "FAIL: $*" >&2; }

# -----------------------------
# 0) OPA unit tests
# -----------------------------

say "==> OPA unit tests"
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:1.10.0 test /policies -v >/dev/null
ok "OPA tests passed"

# -----------------------------
# 1) Bring stack up
# -----------------------------

say "==> Ensuring stack is up (core + federated)"
# Do not rebuild here; images should already be built in CI
# This keeps the smoke test fast and predictable.
eval "$COMPOSE up -d --remove-orphans >/dev/null"
eval "$COMPOSE ps"

# -----------------------------
# 2) Container health handling
# -----------------------------

say "==> Waiting for containers to be healthy"

# Services we care about for overlay smoke
need_healthy=(
  opa
  nats
  minio
  loki
  orchestrator
  ingestors
  fl_coordinator
  consent_registry
  evidence_bundler
)

health_of() {
  local svc="$1"
  # Grab the first container for the service
  local cid
  cid="$(eval "$COMPOSE ps -q \"$svc\"" 2>/dev/null | head -n1 || true)"
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
    if [ $i -ge "$RETRIES" ]; then
      # NATS special-case: Docker health can lag forever while server is actually ready.
      if [ "$svc" = "nats" ]; then
        if eval "$COMPOSE logs \"$svc\"" 2>/dev/null | grep -q "Server is ready"; then
          ok "nats ready (healthcheck never flipped, using log heuristic)"
          break
        fi
      fi

      err "$svc did not become healthy (last status: $status)"
      eval "$COMPOSE logs --tail=80 \"$svc\"" || true
      exit 1
    fi

    sleep "$SLEEP"
  done
done

# -----------------------------
# 3) HTTP-level checks
# -----------------------------

wait_http() {
  local method="$1" url="$2" body="${3:-}"
  local i=0

  while :; do
    if [ "$method" = "GET" ]; then
      if $CURL "$url" >/dev/null 2>&1; then
        return 0
      fi
    else
      if printf '%s' "$body" | $CURL -X "$method" -d @- "$url" >/dev/null 2>&1; then
        return 0
      fi
    fi

    i=$((i+1))
    if [ $i -ge "$RETRIES" ]; then
      return 1
    fi
    sleep "$SLEEP"
  done
}

say "==> Service HTTP checks"

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

if [ "$fail" -eq 0 ]; then
  say "All green."
  exit 0
else
  say "One or more checks failed."
  exit 1
fi
