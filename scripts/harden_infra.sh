#!/usr/bin/env bash
set -Eeuo pipefail

BASE=infra/docker-compose.yml
OVR=infra/docker-compose.hardening.override.yml

cat >"$OVR" <<'YAML'
services:
  orchestrator:
    # reliable restarts + resource hygiene
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp:rw,size=64m,mode=1777
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    # Uvicorn handles signals; this constrains file handles
    ulimits:
      nofile: 65535
    # rotate logs on host so disks don’t fill
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
    # (optional) keep-alives short so dead clients free quickly
    environment:
      - UVICORN_TIMEOUT_KEEP_ALIVE=5

  frontend:
    restart: unless-stopped
    # nginx needs a couple writable dirs; keep root fs read-only
    read_only: true
    tmpfs:
      - /var/cache/nginx:rw,size=128m,mode=0755
      - /var/run:rw,size=16m,mode=0755
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
    ulimits:
      nofile: 65535
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
YAML

echo "==> Wrote $OVR"
echo "==> Bringing stack up with hardening override…"
docker compose -f "$BASE" -f "$OVR" up -d --build

echo "==> Done. (Use both files for future compose commands.)"
