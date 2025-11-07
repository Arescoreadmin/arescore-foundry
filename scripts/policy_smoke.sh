#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

OPA_URL="${OPA_URL:-http://localhost:8181}"

echo "[policy_smoke] OPA_URL=${OPA_URL}"

echo "[policy_smoke] Checking OPA is up via /v1/data/system/version…"
curl -s "${OPA_URL}/v1/data/system/version" | jq || {
  echo "[policy_smoke] OPA not responding. Is the container running?"
  exit 1
}

echo
echo "[policy_smoke] Top-level data keys (actual):"
curl -s "${OPA_URL}/v1/data" | jq '.result | keys' || true

echo
echo "[policy_smoke] GLOBAL training gate (policies/training_gate.rego) – expect allow:true:"
curl -s -w "\n[status:%{http_code}]\n" \
  -X POST "${OPA_URL}/v1/data/foundry/training_gate/allow" \
  -H "content-type: application/json" \
  -d '{
    "input": {
      "dataset": {"id": "ds1"},
      "model":   {"hash": "h1"},
      "tokens":  {"consent": {"signature": "s"}}
    }
  }'

echo
echo "[policy_smoke] GLOBAL training gate – expect allow:false (missing fields):"
curl -s -w "\n[status:%{http_code}]\n" \
  -X POST "${OPA_URL}/v1/data/foundry/training_gate/allow" \
  -H "content-type: application/json" \
  -d '{
    "input": {
      "dataset": {"id": ""},
      "model":   {"hash": ""},
      "tokens":  {"consent": {"signature": ""}}
    }
  }'

echo
echo "[policy_smoke] CONTAINER training gate ( _container_policies ) – expect allow:true if loaded:"
curl -s -w "\n[status:%{http_code}]\n" \
  -X POST "${OPA_URL}/v1/data/foundry/training/allow" \
  -H "content-type: application/json" \
  -d '{
    "input": {
      "metadata": {"labels": ["class:netplus"]},
      "limits":   {"attacker_max_exploits": 0},
      "network":  {"egress": "deny"}
    }
  }'

echo
echo "[policy_smoke] CONTAINER training gate – expect allow:false:"
curl -s -w "\n[status:%{http_code}]\n" \
  -X POST "${OPA_URL}/v1/data/foundry/training/allow" \
  -H "content-type: application/json" \
  -d '{
    "input": {
      "metadata": {"labels": []},
      "limits":   {"attacker_max_exploits": 5},
      "network":  {"egress": "allow"}
    }
  }'

echo
echo "[policy_smoke] Done."
