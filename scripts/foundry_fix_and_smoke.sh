#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-/opt/arescore-foundry}
ENV_FILE=${ENV_FILE:-/etc/arescore-foundry.env}

need(){ command -v "$1" >/dev/null || { echo "missing $1"; exit 2; }; }
need docker
need sed
need tee

echo "==> Rewriting Rego to OPA v1 syntax (adds 'if' and proper default ':=')"
sudo install -d "$BASE/policies"

# foundry.rego (helpers)
sudo tee "$BASE/policies/foundry.rego" >/dev/null <<'REGO'
package foundry

has_label(v) if {
  some i
  input.metadata.labels[i] == v
}

net_denied if {
  input.network.egress == "deny"
}

zero_exploits if {
  input.limits.attacker_max_exploits == 0
}
REGO

# training_gate.rego (policy)
sudo tee "$BASE/policies/training_gate.rego" >/dev/null <<'REGO'
package foundry.training

default allow := false

allow if {
  data.foundry.has_label("class:netplus")
  data.foundry.zero_exploits
  data.foundry.net_denied
}
REGO

# Optional tests updated to v1 (harmless if unused)
sudo tee "$BASE/policies/training_gate_test.rego" >/dev/null <<'REGO'
package foundry.training

test_allow_true if {
  data.foundry.training.allow with input as {
    "metadata": {"labels": ["class:netplus"]},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}

test_allow_false_missing_label if {
  not data.foundry.training.allow with input as {
    "metadata": {"labels": []},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}
REGO

echo "==> Pinning OPA image to 1.10.0 and ensuring command flags are correct"
sudo sed -i '
  s#^\(\s*image:\s*\)openpolicyagent/opa:.*#\1openpolicyagent/opa:1.10.0#;
  s#^\(\s*command:\s*\)\[.*#\1["run","--server","--addr=0.0.0.0:8181","--log-level=info","/policies"]#;
' "$BASE/compose.yml"

# If your base compose had a user: drop it; re-add later if you must
sudo sed -i '/^\s*user:\s*/d' "$BASE/compose.yml" || true

echo "==> Writing compose.override.yml (unified network + OPA native healthcheck)"
sudo tee "$BASE/compose.override.yml" >/dev/null <<'YML'
networks:
  core:
    driver: bridge

services:
  opa:
    networks: [core]
    ports: ["127.0.0.1:8181:8181"]
    healthcheck:
      test: ["CMD","opa","eval","--format=raw","--fail","--server","http://127.0.0.1:8181","true"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s

  orchestrator:
    networks: [core]
    depends_on:
      opa:
        condition: service_healthy
YML

echo "==> Validating policies compile on OPA 1.10.0"
printf '{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}' \
  | docker run --rm -i -v "$BASE/policies":/policies:ro openpolicyagent/opa:1.10.0 \
      eval -b /policies --stdin-input 'data.foundry.training.allow' >/dev/null
printf '%s' '{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}' \
| docker run --rm -i -v "$BASE/policies":/policies:ro openpolicyagent/opa:1.10.0 \
    eval -b /policies --stdin-input 'data.foundry.training.allow' >/dev/null

echo "==> Restarting stack cleanly"
docker compose --env-file "$ENV_FILE" -f "$BASE/compose.yml" -f "$BASE/compose.override.yml" down || true
docker compose --env-file "$ENV_FILE" -f "$BASE/compose.yml" -f "$BASE/compose.override.yml" up -d

echo "==> Waiting for OPA health..."
for i in {1..20}; do
  if docker exec -i arescore-foundry-opa-1 \
     opa eval --format=raw --fail --server http://127.0.0.1:8181 'true' >/dev/null 2>&1; then
    echo "OPA healthy"
    break
  fi
  sleep 1
  [ $i -eq 20 ] && { echo "OPA failed health"; exit 1; }
done

echo "==> Smoke: OPA and Orchestrator"
need jq || true # optional, but handy

# OPA direct
printf '%s' '{"input":{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}}' \
| curl -fsS http://127.0.0.1:8181/v1/data/foundry/training/allow -H 'content-type: application/json' -d @- \
| tee /dev/stderr | grep -q '"result":true'

# Orchestrator health and decision
curl -fsS http://127.0.0.1:8080/health >/dev/null
printf '%s' '{"metadata":{"labels":["class:netplus"]},"limits":{"attacker_max_exploits":0},"network":{"egress":"deny"}}' \
| curl -fsS http://127.0.0.1:8080/scenarios -H 'content-type: application/json' -d @- \
| tee /dev/stderr | grep -q '"allowed":true'

echo "==> All green."
