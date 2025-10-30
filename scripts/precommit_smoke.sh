#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "— Compose sanity…"
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null

echo "— Policy hygiene guard…"
if [[ -x scripts/ci_guard_rego_heads.sh ]]; then
  scripts/ci_guard_rego_heads.sh
else
  echo "WARN: scripts/ci_guard_rego_heads.sh not found/executable; skipping head guard"
fi

echo "— Bring up OPA + orchestrator cleanly…"
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml up -d --force-recreate opa orchestrator

echo "— Wait for OPA health…"
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8181/health >/dev/null; then
    echo "OPA OK"; break
  fi
  sleep 1
  [[ $i -eq 60 ]] && { echo "FAIL: OPA never became healthy"; docker logs --tail=200 arescore-foundry-opa-1; exit 1; }
done

echo "— Wait for Orchestrator health…"
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null; then
    echo "Orchestrator OK"; break
  fi
  sleep 1
  [[ $i -eq 60 ]] && { echo "FAIL: Orchestrator never became healthy"; docker logs --tail=200 orchestrator; exit 1; }
done

echo "— Compile + test policies inside official OPA image…"
docker run --rm -v "$PWD/policies:/policies:ro" openpolicyagent/opa:0.67.0 test -v /policies

echo "— Gate TRUE probe (should be true)…"
curl -fsS http://127.0.0.1:8181/v1/data/foundry/training/allow \
  -H 'content-type: application/json' -d @- <<< '{
    "input": {
      "metadata": { "labels": ["class:netplus"] },
      "limits":   { "attacker_max_exploits": 0 },
      "network":  { "egress": "deny" }
    }
  }' | jq -e '.result == true' >/dev/null

echo "— Gate FALSE probe (should be false)…"
curl -fsS http://127.0.0.1:8181/v1/data/foundry/training/allow \
  -H 'content-type: application/json' -d @- <<< '{
    "input": {
      "metadata": { "labels": ["foo"] },
      "limits":   { "attacker_max_exploits": 0 },
      "network":  { "egress": "deny" }
    }
  }' | jq -e '.result == false' >/dev/null

echo "— Container states…"
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'opa|orchestrator' || true

echo "✅ Pre-commit smoke passed."
