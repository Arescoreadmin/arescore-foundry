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

# Service probes (port:path) — HARD FAIL
PROBES=(
  "8080:/health" "8080:/live" "8080:/ready"
  "9092:/health" "9092:/live" "9092:/ready"
  "9093:/health" "9093:/live" "9093:/ready"
  "9094:/health" "9094:/live" "9094:/ready"
)

# “Business” endpoints — SOFT (non-fatal)
# Format: "METHOD PORT PATH"
SOFT_PROBES=(
  "POST 9093 /consent/training/optin"
  "GET  9093 /crl"
)

# ---------------------------
# Helpers
# ---------------------------
info(){ printf "\033[1;34m==> %s\033[0m\n" "$*"; }
ok(){   printf "\033[1;32m==> OK: %s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33mWARN: %s\033[0m\n" "$*"; }
die(){  printf "\033[1;31mERR: %s\033[0m\n" "$*"; exit 1; }

ensure_compose_parses() {
  docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" config >/dev/null \
    || die "compose validation failed"
}

normalize_depends_on() {
  local file="$1"
  python3 - "$file" <<'PY' || true
import sys, yaml
p = sys.argv[1]
try:
    data = yaml.safe_load(open(p)) or {}
except Exception:
    sys.exit(0)
svcs = data.get("services") or {}
changed = False
for name, svc in list(svcs.items()):
    if isinstance(svc, dict) and "depends_on" in svc:
        deps = svc["depends_on"]
        if isinstance(deps, dict):
            svcs[name]["depends_on"] = list(deps.keys())
            changed = True
if changed:
    yaml.safe_dump(data, open(p, "w"), sort_keys=False)
PY
}

pin_opa_digest() {
  local file="$1"
  sed -Ei 's#(image:[[:space:]]*)openpolicyagent/opa[:@][^[:space:]]*#\1'"$OPA_IMG_DIGEST"'#' "$file" || true
}

probe_http() {
  local port="$1" path="$2" method="${3:-GET}"
  if [[ "$method" == "GET" ]]; then
    curl -fsS "http://127.0.0.1:${port}${path}" >/dev/null
  else
    curl -fsS -X "$method" "http://127.0.0.1:${port}${path}" >/dev/null
  fi
}

# ---------------------------
# 1) OPA unit tests
# ---------------------------
info "Validating OPA policies (OPA unit tests)"
docker run --rm -v "${POL_DIR}:/policies:ro" "$OPA_TEST_IMG" test -v /policies >/dev/null \
  && ok "OPA tests passed"

# ---------------------------
# 2) Compose hygiene
# ---------------------------
info "Backing up ${BASE_COMPOSE}"
cp -f "$BASE_COMPOSE" "${BASE_COMPOSE}.bak.$(date +%s)"

# Remove illegal top-level env_file if helper exists
if [[ -x scripts/strip_root_env_file.sh ]]; then
  info "Removing illegal top-level env_file (if present)"
  scripts/strip_root_env_file.sh >/dev/null || true
fi

info "Ensuring OPA image is pinned to digest"
pin_opa_digest "$BASE_COMPOSE"

info "Normalizing depends_on (base & federated)"
normalize_depends_on "$BASE_COMPOSE"
normalize_depends_on "$FED_COMPOSE"

info "Validating merged compose"
ensure_compose_parses
ok "compose parses"

# ---------------------------
# 3) Build & start
# ---------------------------
info "Building images"
docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" build

info "Starting stack"
docker compose -f "$BASE_COMPOSE" -f "$FED_COMPOSE" up -d

# ---------------------------
# 4) Health probes (hard fail)
# ---------------------------
info "Probing service endpoints"
for pp in "${PROBES[@]}"; do
  port="${pp%%:*}"
  path="${pp#*:}"
  if probe_http "$port" "$path" "GET"; then
    ok "${port}${path}"
  else
    die "Probe failed: ${port}${path}"
  fi
done

# ---------------------------
# 5) Soft business probes
# ---------------------------
for triple in "${SOFT_PROBES[@]}"; do
  read -r method port path <<<"$triple"
  if probe_http "$port" "$path" "$method"; then
    ok "$(printf '%s %s%s' "$method" "$port" "$path")"
  else
    warn "$(printf 'Soft probe failed (non-fatal): %s %s%s' "$method" "$port" "$path")"
  fi
done

# ---------------------------
# 6) Overlay smoke (end-to-end)
# ---------------------------
if grep -q '^overlay-smoke:' Makefile 2>/dev/null; then
  info "Running overlay-smoke via make"
  make overlay-smoke
elif [[ -x scripts/smoke_overlay.sh ]]; then
  info "Running overlay-smoke via script"
  bash scripts/smoke_overlay.sh
else
  warn "overlay-smoke step skipped (no target or script found)"
fi

ok "All green ✅"
