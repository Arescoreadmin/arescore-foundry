#!/bin/bash
set -Eeuo pipefail

note(){ printf '— %s\n' "$*"; }

# Use base compose; include OPA override if present
compose_files=(-f infra/docker-compose.yml)
[ -f infra/compose.opa.yml ] && compose_files+=(-f infra/compose.opa.yml)

note "Validating compose config"
docker compose "${compose_files[@]}" config >/dev/null && echo "✅ compose config valid"

note "Quick sanity: orchestrator build context and port"
block="$(docker compose "${compose_files[@]}" config | sed -n '/^  orchestrator:/,/^  [^ ]/p')"
echo "$block" | grep -q 'services/orchestrator' || { echo "❌ compose does not point to services/orchestrator"; exit 1; }
echo "$block" | grep -Eq 'target:\s*8080' || { echo "❌ orchestrator target port must be 8080"; exit 1; }
echo "✅ compose points to services/orchestrator and target:8080"

note "Rebuild orchestrator (no cache) and force-recreate"
docker compose "${compose_files[@]}" build --no-cache orchestrator
docker compose "${compose_files[@]}" up -d orchestrator --force-recreate --no-deps

note "Health checks"
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null; then
    echo "✅ orchestrator healthy"; break
  fi
  sleep 1
done

# Probe OPA only if it's part of the effective stack
if docker compose "${compose_files[@]}" ps --services | grep -q '^opa$'; then
  for i in {1..30}; do
  curl -fsS http://127.0.0.1:8080/health >/dev/null && { echo "✅ orchestrator healthy"; break; }
  sleep 1
done
fi

note "Done"
