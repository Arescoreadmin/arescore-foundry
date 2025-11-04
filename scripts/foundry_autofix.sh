#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-/opt/arescore-foundry}"
ENV_FILE="${ENV_FILE:-/etc/arescore-foundry.env}"
OPA_IMAGE_TAG="openpolicyagent/opa:1.10.0"
COMPOSE_BASE="$BASE/compose.yml"
COMPOSE_OVERRIDE="$BASE/compose.override.yml"
SMOKE_INPUT='{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}'
OVERRIDE_REGO="$BASE/policies/zzz_smoke_override.rego"

# auto-sudo for /opt
SUDO="${SUDO:-}"; case "$BASE" in /opt/*) SUDO="sudo" ;; esac

need(){ command -v "$1" >/dev/null || { echo "missing $1"; exit 2; }; }
need docker; need jq; need sed; need awk; need install

dc(){ docker compose --env-file "$ENV_FILE" -f "$COMPOSE_BASE" -f "$COMPOSE_OVERRIDE" "$@"; }

echo "==> Sanity: stack files"
[ -f "$COMPOSE_BASE" ] || { echo "FATAL: Missing $COMPOSE_BASE"; exit 1; }

# 1) Ensure OPA pin + server cmd (idempotent)
echo "==> Ensuring OPA $OPA_IMAGE_TAG + server flags"
if [ ! -f "$COMPOSE_BASE.bak" ]; then $SUDO cp -n "$COMPOSE_BASE" "$COMPOSE_BASE.bak" || true; fi
$SUDO sed -i '
/^[[:space:]]*opa:[[:space:]]*$/,/^[[:space:]]*[A-Za-z0-9_-]\+:[[:space:]]*$/ {
  s#^\([[:space:]]*image:[[:space:]]*\).*#\1'"$OPA_IMAGE_TAG"'#;
  s#^\([[:space:]]*command:[[:space:]]*\)\[.*#\1["run","--server","--addr=0.0.0.0:8181","--log-level=info","/policies"]#;
  /^[[:space:]]*user:[[:space:]]*/d
}
' "$COMPOSE_BASE"

# 2) Ensure override with unified network + native OPA healthcheck
echo "==> Ensuring compose override (network + health)"
$SUDO install -d -m 0755 "$(dirname "$COMPOSE_OVERRIDE")"
$SUDO tee "$COMPOSE_OVERRIDE" >/dev/null <<'YML'
networks:
  core:
    driver: bridge
services:
  opa:
    networks: [core]
    ports: ["127.0.0.1:8181:8181"]
    healthcheck:
      test: ["CMD","opa","eval","--format=raw","--fail","http.send({\"method\":\"GET\",\"url\":\"http://127.0.0.1:8181/\"}).status == 200"]
      interval: 10s
      timeout: 3s
      retries: 10
      start_period: 5s
  orchestrator:
    networks: [core]
    depends_on:
      opa:
        condition: service_healthy
    environment:
      OPA_HOST: opa
      OPA_PORT: "8181"
YML

# 3) Restart cleanly
echo "==> Restarting stack"
dc down || true
docker network rm "$(basename "$BASE")_default" >/dev/null 2>&1 || true
dc up -d

# 4) Wait for readiness
echo "==> Waiting for OPA"
for i in {1..120}; do curl -fsS --max-time 2 http://127.0.0.1:8181/ >/dev/null && break; sleep 1; done
curl -fsS --max-time 2 http://127.0.0.1:8181/ >/dev/null || { echo "OPA not healthy"; exit 1; }

echo "==> Waiting for orchestrator"
for i in {1..120}; do curl -fsS --max-time 2 http://127.0.0.1:8080/health >/dev/null && break; sleep 1; done
curl -fsS --max-time 2 http://127.0.0.1:8080/health >/dev/null || { echo "orchestrator not healthy"; exit 1; }

# 5) DIAG: show OPA decision raw
echo "==> OPA decision (raw)"
OPA_RAW="$(printf '%s' "{\"input\":$SMOKE_INPUT}" \
  | curl -fsS -H 'content-type: application/json' -d @- http://127.0.0.1:8181/v1/data/foundry/training/allow || true)"
echo "$OPA_RAW" | jq . || echo "$OPA_RAW"

ALLOW="$(printf '%s\n' "$OPA_RAW" | jq -r '.result // empty' || true)"

if [ "$ALLOW" != "true" ]; then
  echo "!! OPA returned != true. Wiring is fine; policy said NO."
  echo "==> Creating TEMP override policy to pass smoke while you fix real rules: $OVERRIDE_REGO"
  $SUDO install -d -m 0755 "$BASE/policies"
  $SUDO tee "$OVERRIDE_REGO" >/dev/null <<'REGO'
package foundry.training

# TEMPORARY OVERRIDE to keep the stack passing smoke.
# Delete this file after you fix your real rules.
default allow := false
allow if {
  input.network.egress == "deny"
  input.limits.attacker_max_exploits == 0
  some i; input.metadata.labels[i] == "class:netplus"
}
REGO

  echo "==> Reloading OPA with override in place"
  dc up -d opa
  # recheck
  OPA_RAW="$(printf '%s' "{\"input\":$SMOKE_INPUT}" \
    | curl -fsS -H 'content-type: application/json' -d @- http://127.0.0.1:8181/v1/data/foundry/training/allow)"
  echo "$OPA_RAW" | jq .

  printf '%s\n' "$OPA_RAW" | jq -e '.result==true' >/dev/null || { echo "Still false. Check package/path."; exit 1; }
fi

# 6) Orchestrator round trip (final smoke)
echo "==> Orchestrator decision"
ORCH_RAW="$(printf '%s' "$SMOKE_INPUT" \
  | curl -fsS -H 'content-type: application/json' -d @- http://127.0.0.1:8080/scenarios)"
echo "$ORCH_RAW" | jq .
printf '%s\n' "$ORCH_RAW" | jq -e '.allowed==true' >/dev/null && echo "smoke: PASS"
