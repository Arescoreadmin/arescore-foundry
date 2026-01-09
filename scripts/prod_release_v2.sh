# ensure orchestrator Dockerfile is sane
./scripts/fix_orchestrator_dockerfile.sh

#!/usr/bin/env bash
# scripts/prod_release_v2.sh
# Production roll-out: validate OPA, build, boot, wait-for-health, smoke.
set -euo pipefail

# ---------- Config ----------
OPA_IMAGE_DIGEST="openpolicyagent/opa@sha256:c0814ce7811ecef8f1297a8e55774a1d5422e5c18b996b665acbc126124fab19"
BASE_COMPOSE="compose.yml"
FEDERATED_OVERLAY="compose.federated.yml"
STAGING_OVERLAY="compose.staging.yml"   # included only if PROD_USE_STAGING=1
OPA_POLICIES_DIR="policies"
ORCH_SERVICE="orchestrator"
ORCH_HEALTH_URL="http://127.0.0.1:8080/health"

# Endpoints to smoke (host-published)
FL_COORD_HEALTH="http://127.0.0.1:9092/health"
CONSENT_OPTIN="http://127.0.0.1:9093/consent/training/optin"
CONSENT_CRL="http://127.0.0.1:9093/crl"
EVIDENCE_HEALTH="http://127.0.0.1:9094/health"

# ---------- UI helpers ----------
c() { printf "\033[%sm" "$1"; }
info() { c 1; echo "==> $*"; c 0; }
ok()   { c "32m"; echo "OK: $*"; c 0; }
warn() { c "33m"; echo "WARN: $*"; c 0; }
err()  { c "31m"; echo "ERROR: $*" >&2; c 0; }

# ---------- Repo root ----------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"
info "Repo root: $REPO_ROOT"

# ---------- Sanity: needed tools ----------
command -v docker >/dev/null || { err "docker not found"; exit 2; }
command -v docker compose >/dev/null || { err "docker compose plugin not found"; exit 2; }
command -v curl >/dev/null || { err "curl not found"; exit 2; }

# ---------- Helper: waiters ----------
wait_for_http() {
  local url="$1" tries="${2:-30}" sleep_s="${3:-2}"
  local i=1
  while [ $i -le "$tries" ]; do
    if curl -fsS "$url" >/dev/null; then ok "$url"; return 0; fi
    echo "WAIT [$i/$tries]: $url"; sleep "$sleep_s"; i=$((i+1))
  done
  err "$url did not become ready in time"; return 1
}

wait_for_orchestrator_in_container_net() {
  local cid="$1" tries="${2:-30}" sleep_s="${3:-2}"
  local i=1
  while [ $i -le "$tries" ]; do
    if docker run --rm --network "container:${cid}" curlimages/curl:8.10.1 \
      -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
      ok "orchestrator /health (container net)"
      return 0
    fi
    echo "WAIT [$i/$tries]: orchestrator (container net)"; sleep "$sleep_s"; i=$((i+1))
  done
  err "orchestrator did not become ready (container net)"; return 1
}

# ---------- Step 1: OPA unit tests ----------
info "Validating OPA policies (opa:1.10.0)"
docker run --rm -v "$PWD/$OPA_POLICIES_DIR":/policies:ro "$OPA_IMAGE_DIGEST" \
  test /policies -v
ok "OPA unit tests passed"

# ---------- Step 2: ensure compose.yml pins OPA digest ----------
info "Ensuring compose.yml OPA image digest is pinned"
# Replace any openpolicyagent/opa tag/digest with the pinned digest
# Uses a safe delimiter and regex to match either :tag or @sha
sed -Ei 's#(image:\s*)openpolicyagent/opa[:@][^[:space:]]*#\1'"$OPA_IMAGE_DIGEST"'#' "$BASE_COMPOSE"


# ---------- Step 3: choose compose stack ----------
COMPOSE_ARGS=(-f "$BASE_COMPOSE" -f "$FEDERATED_OVERLAY")
if [ "${PROD_USE_STAGING:-0}" = "1" ] && [ -f "$STAGING_OVERLAY" ]; then
  info "Including staging overlay (PROD_USE_STAGING=1)"
  COMPOSE_ARGS+=(-f "$STAGING_OVERLAY")
fi

# ---------- Step 4: Compose validation ----------
info "Validating merged compose"
docker compose "${COMPOSE_ARGS[@]}" config >/dev/null
ok "Compose validated"

# ---------- Step 5: Build images ----------
info "Building images"
docker compose "${COMPOSE_ARGS[@]}" build --no-cache

# ---------- Step 6: Start stack ----------
info "Starting stack"
docker compose "${COMPOSE_ARGS[@]}" up -d

# ---------- Step 7: Wait for orchestrator ----------
info "Waiting for orchestrator health"
# Try host-published port first
if ! wait_for_http "$ORCH_HEALTH_URL" 30 2; then
  # Fallback to container-net probe if port mapping changes
  ORCH_CID="$(docker compose "${COMPOSE_ARGS[@]}" ps -q "$ORCH_SERVICE")"
  [ -n "${ORCH_CID:-}" ] || { err "Could not resolve orchestrator container id"; exit 1; }
  wait_for_orchestrator_in_container_net "$ORCH_CID" 30 2
fi

# ---------- Step 8: End-to-end overlay smoke ----------
info "Running overlay smokes"
wait_for_http "$FL_COORD_HEALTH" 30 2
# consent opt-in requires POST
i=1; until curl -fsS -X POST "$CONSENT_OPTIN" >/dev/null; do
  [ $i -ge 30 ] && { err "consent opt-in not ready"; exit 1; }
  echo "WAIT [$i/30]: consent opt-in"; sleep 2; i=$((i+1))
done
ok "consent_opt_in"

wait_for_http "$CONSENT_CRL" 30 2
wait_for_http "$EVIDENCE_HEALTH" 30 2

ok "All health checks green"

# ---------- Summary ----------
c "32m"; cat <<'TXT'
Release complete:
  - OPA policies validated
  - Compose merged & validated
  - Images built and stack started
  - Orchestrator healthy
  - Federated overlay endpoints healthy
TXT
c 0
