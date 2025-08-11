#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="${INFRA:-$ROOT/infra}"

# Build compose file args (use override if present)
DC=(-f "$INFRA/docker-compose.yml")
[ -f "$INFRA/docker-compose.override.yml" ] && DC+=(-f "$INFRA/docker-compose.override.yml")

c(){ echo "+ $*"; eval "$*"; }

wait_for(){
  local url="$1" name="${2:-$1}" tries="${3:-30}" sleep_s="${4:-1}"
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "OK: $name"
      return 0
    fi
    sleep "$sleep_s"
  done
  echo "TIMEOUT: $name"; return 1
}

echo "==> Up (build)"
c "docker compose ${DC[*]} up -d --build"

# Only runtime-patch if the live config doesn't already have the directives
if ! docker compose "${DC[@]}" exec -T frontend sh -lc 'nginx -T 2>/dev/null | grep -q "proxy_connect_timeout"'; then
  echo "==> Apply frontend nginx patch (runtime)"
  STACK_DIR="$INFRA" "$ROOT/scripts/patch_frontend_nginx.sh" apply
  trap 'STACK_DIR="$INFRA" "$ROOT/scripts/patch_frontend_nginx.sh" revert || true' EXIT
fi

echo "==> Probes"
wait_for "http://localhost:3000/ready"         "frontend /ready"                20 1
wait_for "http://localhost:3000/api/ready"     "frontend → orchestrator /ready" 20 1
wait_for "http://localhost:8000/health"        "orchestrator /health"           30 1 || true
wait_for "http://localhost:8080/health"        "log_indexer /health"            30 1 || true

echo "==> PASS"
