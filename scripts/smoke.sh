#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="$ROOT/infra"
DC=(-f "$INFRA/docker-compose.yml")
[[ -f "$INFRA/docker-compose.override.yml" ]] && DC+=(-f "$INFRA/docker-compose.override.yml")
[[ -f "$INFRA/docker-compose.health.yml"   ]] && DC+=(-f "$INFRA/docker-compose.health.yml")
[[ -f "$INFRA/docker-compose.depends.yml"  ]] && DC+=(-f "$INFRA/docker-compose.depends.yml")
[[ -f "$INFRA/docker-compose.security.yml" ]] && DC+=(-f "$INFRA/docker-compose.security.yml")

have_wait(){
  docker compose version 2>/dev/null | awk 'match($0,/v2\.([0-9]+)/,m){ if (m[1] >= 20) {print "yes"} }' | grep -q yes
}

echo "==> Up"
if have_wait; then
  docker compose "${DC[@]}" up -d --build --wait --wait-timeout 90
else
  docker compose "${DC[@]}" up -d --build
fi

# Probes
curl -fsS http://localhost:3000/ready >/dev/null
curl -fsS http://localhost:3000/api/ready >/dev/null
curl -fsS http://localhost:8000/health >/dev/null
curl -fsS http://localhost:8080/health >/dev/null
echo "==> PASS"
