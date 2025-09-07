#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-apply}"
ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
INFRA_DIR="$ROOT_DIR/infra"
BASE="$INFRA_DIR/docker-compose.yml"
OVR="$INFRA_DIR/docker-compose.override.yml"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
need docker
need curl

write_override() {
  mkdir -p "$INFRA_DIR"
  cat > "$OVR" <<'YAML'
services:
  orchestrator:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
  log_indexer:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
YAML
  echo "✓ Wrote $OVR"
}

wait_http() {
  local url="$1" label="${2:-$1}" tries="${3:-20}" sleep_s="${4:-2}"
  printf "Waiting for %s" "$label"
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then echo -e "\nOK: $label"; return 0; fi
    printf "."
    sleep "$sleep_s"
  done
  echo -e "\nTIMEOUT: $label"
  return 1
}

smoke() {
  wait_http "http://localhost:3000/ready"       "frontend /ready"
  wait_http "http://localhost:3000/api/ready"   "frontend → orchestrator /api/ready"
  wait_http "http://localhost:8000/health"      "orchestrator /health"
  wait_http "http://localhost:8080/health"      "log_indexer /health"
  echo "==> PASS"
}

case "$cmd" in
  apply|"")
    [ -f "$BASE" ] || { echo "Compose file not found: $BASE"; exit 1; }
    write_override
    docker compose -f "$BASE" -f "$OVR" up -d
    smoke
    ;;
  smoke)
    smoke
    ;;
  status)
    docker compose -f "$BASE" ${OVR:+-f "$OVR"} ps
    ;;
  revert)
    if [ -f "$OVR" ]; then
      rm -f "$OVR"
      echo "✓ Removed $OVR"
      docker compose -f "$BASE" up -d
      smoke
    else
      echo "No override to remove."
    fi
    ;;
  *)
    echo "Usage: $0 [apply|smoke|status|revert]"
    exit 2
    ;;
esac
