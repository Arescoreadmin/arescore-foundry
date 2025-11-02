#!/usr/bin/env bash
set -euo pipefail

# ========= Config =========
OPA_UNIT_IMG="openpolicyagent/opa:1.10.0"
OPA_IMAGE_DIGEST="openpolicyagent/opa@sha256:c0814ce7811ecef8f1297a8e55774a1d5422e5c18b996b665acbc126124fab19"

BASE_COMPOSE="compose.yml"
FED_COMPOSE="compose.federated.yml"

# Ports for smokes
PORTS=(8080 9092 9093 9094)
EPS=(health live ready)

# ========= Helpers =========
info(){ printf "\033[1;34m==> %s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33mWARN: %s\033[0m\n" "$*" >&2; }
die(){  printf "\033[1;31mERR: %s\033[0m\n"  "$*" >&2; exit 1; }

require(){ command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

root="$(pwd)"
[ -f "$BASE_COMPOSE" ] || die "No $BASE_COMPOSE at $root"
[ -f "$FED_COMPOSE" ]  || warn "No $FED_COMPOSE; proceeding with base only"

require docker
require awk
require sed
require python3
require grep
# PyYAML used by normalize step
python3 -c 'import yaml' 2>/dev/null || die "PyYAML not installed (pip install pyyaml)"

compose_cmd=(docker compose -f "$BASE_COMPOSE")
[ -f "$FED_COMPOSE" ] && compose_cmd+=( -f "$FED_COMPOSE" )

# ========= Step 0: OPA unit tests =========
info "Validating OPA policies (OPA unit tests)"
docker run --rm -v "$root/policies:/policies:ro" "$OPA_UNIT_IMG" test -v /policies >/dev/null \
  && info "OK: OPA tests passed"

# ========= Step 1: sanitize compose.yml =========
info "Backing up $BASE_COMPOSE"
cp "$BASE_COMPOSE" "$BASE_COMPOSE.bak.$(date +%s)"

# 1a) Drop illegal top-level env_file (human-safe; no yq needed)
info "Removing illegal top-level env_file from $BASE_COMPOSE (if present)"
# remove any top-level line like: env_file:  (not indented)
sed -i '1,50{/^[[:space:]]*env_file:/d;}' "$BASE_COMPOSE"

# 1b) Pin OPA image digest (match either :tag or @sha)
info "Ensuring OPA image is pinned to digest"
sed -Ei "s#(image:[[:space:]]*)openpolicyagent/opa[:@][^[:space:]]*#\1${OPA_IMAGE_DIGEST}#g" "$BASE_COMPOSE"

# 1c) Normalize depends_on to array form for validators (base + federated)
normalize_depends(){
  local file="$1"
  [ -f "$file" ] || return 0
  python3 - "$file" <<'PY'
import sys, yaml
p=sys.argv[1]
with open(p) as f:
    d=yaml.safe_load(f) or {}
svcs=(d.get("services") or {})
changed=False
for name, svc in list(svcs.items()):
    if isinstance(svc, dict) and "depends_on" in svc:
        v=svc["depends_on"]
        if isinstance(v, dict):
            svcs[name]["depends_on"]=list(v.keys())
            changed=True
        elif isinstance(v, str):
            svcs[name]["depends_on"]=[v]
            changed=True
with open(p,"w") as f:
    yaml.safe_dump(d, f, sort_keys=False)
print("normalized" if changed else "unchanged")
PY
}
info "Normalizing depends_on (base compose)"
normalize_depends "$BASE_COMPOSE" >/dev/null || true
if [ -f "$FED_COMPOSE" ]; then
  info "Normalizing depends_on (federated compose)"
  normalize_depends "$FED_COMPOSE" >/dev/null || true
fi

# ========= Step 2: validate merged compose =========
info "Validating merged compose"
"${compose_cmd[@]}" config >/dev/null && info "OK: compose parses"

# ========= Step 3: build images (orchestrator always rebuilt) =========
info "Building images"
"${compose_cmd[@]}" build orchestrator >/dev/null
# Optional: build the rest to ensure consistent layers
"${compose_cmd[@]}" build >/dev/null

# ========= Step 4: start stack =========
info "Starting stack"
"${compose_cmd[@]}" up -d --remove-orphans >/dev/null

# ========= Step 5: health smokes with retry =========
probe_http(){
  local url="$1" method="${2:-GET}" body="${3:-}"
  if [ "$method" = "POST" ]; then
    curl -fsS -X POST ${body:+-d "$body"} "$url" >/dev/null
  else
    curl -fsS "$url" >/dev/null
  fi
}

retry(){
  local tries="$1"; shift
  local sleep_s="$1"; shift
  local i
  for i in $(seq 1 "$tries"); do
    if "$@"; then return 0; fi
    sleep "$sleep_s"
  done
  return 1
}

# Core endpoints
info "Probing service endpoints"
for port in "${PORTS[@]}"; do
  for ep in "${EPS[@]}"; do
    retry 30 1 probe_http "http://127.0.0.1:${port}/${ep}" \
      && info "OK: ${port}/${ep}" \
      || die "Failed: ${port}/${ep}"
  done
done

# Consent POST + CRL reads (9093)
retry 30 1 probe_http "http://127.0.0.1:9093/consent/training/optin" POST \
  && info "OK: consent opt-in" \
  || die "Failed: consent opt-in"
retry 30 1 probe_http "http://127.0.0.1:9093/crl" \
  && info "OK: consent CRL" \
  || die "Failed: consent CRL"

info "All green ✅"
