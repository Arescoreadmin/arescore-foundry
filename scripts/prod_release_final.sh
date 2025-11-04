#!/usr/bin/env bash
set -euo pipefail

# ---------------------------
# Config (override via env)
# ---------------------------
OPA_IMG_DIGEST="${OPA_IMG_DIGEST:-openpolicyagent/opa@sha256:c0814ce7811ecef8f1297a8e55774a1d5422e5c18b996b665acbc126124fab19}"
OPA_TEST_IMG="${OPA_TEST_IMG:-openpolicyagent/opa:1.10.0}"
BASE_COMPOSE="${BASE_COMPOSE:-compose.yml}"
FED_COMPOSE="${FED_COMPOSE:-compose.federated.yml}"
POL_DIR="${POL_DIR:-$(pwd)/policies}"

# Probe list (port:path)
PROBES=(
  "8080:/health" "8080:/live" "8080:/ready"
  "9092:/health" "9092:/live" "9092:/ready"
  "9093:/health" "9093:/live" "9093:/ready"
  "9094:/health" "9094:/live" "9094:/ready"
)
# Extra API checks
EXTRA_CHECKS=(
  "POST 9093/consent/training/optin"
  "GET  9093/crl"
)

# ---------------------------
# Helpers
# ---------------------------
info(){ printf "==> %s\n" "$*"; }
ok(){   printf "==> OK: %s\n" "$*"; }
err(){  printf "ERR: %s\n" "$*" >&2; }

retry_curl(){
  # $1 = METHOD, $2 = URL, $3 = max_attempts, $4 = initial_sleep
  local m="$1" u="$2" max="${3:-20}" sleep_s="${4:-0.5}"
  local i=1
  while :; do
    if curl -fsS -X "$m" "$u" >/dev/null; then
      return 0
    fi
    if (( i >= max )); then
      return 1
    fi
    # exponential backoff with cap
    sleep "$sleep_s"
    sleep_s=$(awk -v s="$sleep_s" 'BEGIN{ s*=1.5; if (s>3) s=3; print s }')
    (( i++ ))
  done
}

wait_healthy(){
  # $@ services to wait on
  local svcs=("$@") cid status started=false
  info "Waiting for containers to be healthy"
  for s in "${svcs[@]}"; do
    # resolve container id (robust if service restarts)
    for _ in {1..120}; do
      cid="$(docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" ps -q "$s" || true)"
      [[ -n "$cid" ]] || { sleep 0.5; continue; }
      status="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "starting")"
      if [[ "$status" == "healthy" ]]; then
        ok "$s healthy"
        started=true
        break
      fi
      sleep 0.5
    done
    [[ "$started" == true ]] || { err "$s did not become healthy"; return 1; }
    started=false
  done
}

# ---------------------------
# 1) OPA unit tests
# ---------------------------
info "Validating OPA policies (OPA unit tests)"
docker run --rm -v "$POL_DIR:/policies:ro" "$OPA_TEST_IMG" test -v /policies >/dev/null
ok "OPA tests passed"

# ---------------------------
# 2) Compose hygiene
# ---------------------------
# backup
info "Backing up compose.yml"
cp -f "$BASE_COMPOSE" "$BASE_COMPOSE.bak.$(date +%s)"

# strip illegal top-level env_file if any
info "Removing illegal top-level env_file (if present)"
sed -i '1{/^env_file:/d;}' "$BASE_COMPOSE"

# pin OPA digest
info "Ensuring OPA image is pinned to digest"
sed -Ei 's#(image:[[:space:]]*)openpolicyagent/opa[:@][^[:space:]]*#\1'"$OPA_IMG_DIGEST"'#' "$BASE_COMPOSE"

# normalize depends_on in both files to arrays (validator-friendly)
normalize_depends(){
  python3 - "$1" <<'PY'
import sys, yaml
p=sys.argv[1]
data=yaml.safe_load(open(p)) or {}
svcs=(data.get('services') or {})
for name,svc in list(svcs.items()):
    if isinstance(svc,dict) and 'depends_on' in svc:
        dep=svc['depends_on']
        if isinstance(dep,dict):
            svcs[name]['depends_on']=list(dep.keys())
        elif isinstance(dep,str):
            svcs[name]['depends_on']=[dep]
open(p,'w').write(yaml.dump(data, sort_keys=False))
PY
}
info "Normalizing depends_on (base & federated)"
normalize_depends "$BASE_COMPOSE"
normalize_depends "$FED_COMPOSE"

# validate final merged compose
info "Validating merged compose"
docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" config >/dev/null
ok "compose parses"

# ---------------------------
# 3) Build & up
# ---------------------------
info "Building images"
docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" build
info "Starting stack"
docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" up -d

# ---------------------------
# 4) Wait for health
# ---------------------------
wait_healthy orchestrator fl_coordinator consent_registry evidence_bundler

# ---------------------------
# 5) Probes with retries
# ---------------------------
info "Probing service endpoints"
for pair in "${PROBES[@]}"; do
  port="${pair%%:*}"; path="${pair#*:}"
  if retry_curl GET "http://127.0.0.1:${port}${path}" 40 0.3; then
    ok "${port}${path}"
  else
    err "Probe failed: ${port}${path}"
    exit 1
  fi
done

# Extra API checks
for chk in "${EXTRA_CHECKS[@]}"; do
  read -r method rest <<<"$chk"
  url="http://127.0.0.1:${rest// /}"
  if retry_curl "$method" "$url" 40 0.3; then
    ok "$method ${rest}"
  else
    err "Failed: $method ${rest}"
    exit 1
  fi
done

# ---------------------------
# 6) Overlay smoke (Make)
# ---------------------------
info "Running overlay-smoke"
if make -qp | awk -F: '/^overlay-smoke:/{found=1} END{exit !found}'; then
  make overlay-smoke
else
  info "Make target overlay-smoke not found; calling scripts/smoke_overlay.sh directly"
  bash ./scripts/smoke_overlay.sh
fi

ok "All green ✅"

echo "==> Producing SBOMs + digest report"
ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts}" \
COMPOSE_FILES="-f compose.yml -f compose.federated.yml" \
bash scripts/report_sbom.sh
echo "==> Artifacts ready in ./artifacts"
