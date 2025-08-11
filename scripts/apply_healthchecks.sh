#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-apply}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="${INFRA:-$ROOT/infra}"
BASE="$INFRA/docker-compose.yml"
OVR="$INFRA/docker-compose.override.yml"
HLT="$INFRA/docker-compose.health.yml"

compose_cmd() {
  local files=(-f "$BASE")
  [[ -f "$OVR" ]] && files+=(-f "$OVR")
  [[ -f "$HLT" ]] && files+=(-f "$HLT")
  docker compose "${files[@]}" "$@"
}

write_health_override() {
  cat > "$HLT" <<'YML'
services:
  frontend:
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8080/ready || exit 1"]
      interval: 5s
      timeout: 2s
      retries: 10
      start_period: 5s

  orchestrator:
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import sys,urllib.request;import socket;socket.setdefaulttimeout(2);urllib.request.urlopen('http://localhost:8000/health');sys.exit(0)\" || exit 1"]
      interval: 5s
      timeout: 2s
      retries: 20
      start_period: 5s
YML
}

container_health() {
  local svc="$1"
  local id
  id="$(compose_cmd ps -q "$svc" | tr -d '\r')"
  [[ -n "$id" ]] || { echo "WARN: no container for $svc"; return 1; }
  docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo "none"
}

wait_health() {
  local svc="$1" tries="${2:-60}"
  for _ in $(seq 1 "$tries"); do
    case "$(container_health "$svc")" in
      healthy) echo "OK: $svc healthy"; return 0 ;;
      starting) : ;;
      none) echo "NOTE: $svc has no healthcheck yet"; return 0 ;;
      unhealthy) : ;;
      *) : ;;
    esac
    sleep 1
  done
  echo "WARN: $svc not healthy yet"
  return 1
}

case "$ACTION" in
  apply)
    echo "==> Writing health override: $HLT"
    write_health_override
    echo "==> (Re)creating services with healthchecks"
    compose_cmd up -d --build
    echo "==> Waiting for health..."
    wait_health frontend || true
    wait_health orchestrator || true
    echo "==> Done."
    ;;

  revert)
    if [[ -f "$HLT" ]]; then
      echo "==> Removing $HLT"
      rm -f "$HLT"
      echo "==> Recreating without health override"
      compose_cmd up -d --force-recreate
      echo "==> Done."
    else
      echo "No health override file to remove: $HLT"
    fi
    ;;

  status)
    echo "frontend:    $(container_health frontend)"
    echo "orchestrator: $(container_health orchestrator)"
    ;;

  *)
    echo "usage: $0 {apply|revert|status}" >&2
    exit 2
    ;;
esac
