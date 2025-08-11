#!/usr/bin/env bash
set -Eeuo pipefail

# Verifies all containers are healthy + Nginx is serving /ready and /api/ready.
# If everything passes, commits/pushes your changes.
#
# Usage:
#   bash scripts/verify_lock_in.sh
#   PUSH=1 bash scripts/verify_lock_in.sh      # also push to origin
#   CREATE_PR=1 bash scripts/verify_lock_in.sh  # create PR (requires gh)
#
# Notes:
# - Runs with whatever compose files exist (health/depends/security/nginxbind).
# - Only commits if checks PASS.

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
fail(){ echo "❌ $*"; exit 1; }

ROOT="${ROOT:-$(pwd)}"
INFRA="$ROOT/infra"
PUSH="${PUSH:-0}"
CREATE_PR="${CREATE_PR:-0}"

DC=(-f "$INFRA/docker-compose.yml")
for f in docker-compose.override.yml docker-compose.health.yml docker-compose.depends.yml docker-compose.security.yml docker-compose.nginxbind.yml; do
  [[ -f "$INFRA/$f" ]] && DC+=(-f "$INFRA/$f")
done
compose(){ docker compose "${DC[@]}" "$@"; }

trap 'ec=$?; [[ $ec -eq 0 ]] && exit 0; echo; say "compose ps"; compose ps || true; echo; say "recent logs"; compose logs --tail=120 || true; exit $ec' ERR

health_of(){
  local svc="$1" id status
  id="$(compose ps -q "$svc" | tr -d "\r" || true)"
  [[ -n "$id" ]] || { echo "none"; return; }
  status="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo "none")"
  echo "$status"
}

wait_health(){
  local timeout="${1:-240}" start="$SECONDS"
  say "Waiting up to ${timeout}s for health..."
  while (( SECONDS - start < timeout )); do
    local ok=1
    for s in orchestrator frontend log_indexer; do
      if compose ps --services | grep -qx "$s"; then
        [[ "$(health_of "$s")" == "healthy" ]] || ok=0
      fi
    done
    (( ok==1 )) && return 0
    sleep 2
  done
  return 1
}

say "Docker/Compose versions"
docker --version || true
docker compose version || true

say "Validate compose config"
compose config >/dev/null

say "Up (with wait if supported)"
if docker compose version 2>/dev/null | grep -qE 'v2\.(2[0-9]|[3-9][0-9])'; then
  compose up -d --wait --wait-timeout 120 || compose up -d
else
  compose up -d
fi

wait_health 300 || fail "Services not healthy in time."

say "Probe from host"
code=$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000/ready || true)
[[ "$code" == "200" ]] || fail "/ready not 200 (got $code)"
code=$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000/api/ready || true)
[[ "$code" == "200" ]] || fail "/api/ready not 200 (got $code)"
echo "  /ready and /api/ready OK"

# Frontend container checks
FID="$(compose ps -q frontend | tr -d '\r')"
[[ -n "$FID" ]] || fail "frontend container not found"

say "Check Nginx config inside container"
docker exec "$FID" sh -lc 'nginx -t' >/dev/null
docker exec "$FID" sh -lc 'nginx -T | grep -q "location = /api/ready"' || fail "Nginx missing /api/ready location"

say "Check backend reachability from frontend container"
docker exec "$FID" sh -lc 'apk add -q curl >/dev/null 2>&1 || true; curl -fsS http://orchestrator:8000/health >/dev/null' \
  || fail "frontend cannot reach orchestrator:8000/health"

say "Scan logs for nginx errors"
docker logs "$FID" --tail=200 | grep -E '\[emerg\]|\[alert\]|\[crit\]|\[error\]' && fail "Found nginx errors in recent logs" || echo "  no errors found"

say "Summary (health)"
compose ps
echo "frontend:     $(health_of frontend)"
echo "orchestrator: $(health_of orchestrator)"
if compose ps --services | grep -qx log_indexer; then echo "log_indexer:  $(health_of log_indexer)"; fi

say "Git status"
git status --porcelain || true

# Commit only if healthy AND there are changes
if git status --porcelain | grep -q .; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  say "Committing on $BRANCH"
  git add -A
  git commit -m "infra: lock in healthy stack (nginx + healthchecks verified)"
  if (( PUSH )); then
    git push -u origin "$BRANCH"
    echo "Pushed to origin/$BRANCH"
    if (( CREATE_PR )); then
      if command -v gh >/dev/null 2>&1; then
        gh pr create -t "Infra: lock in health & nginx config" -b "All services healthy; /ready and /api/ready verified; nginx config validated."
      else
        echo "gh not found; skipping PR creation."
      fi
    fi
  fi
else
  echo "No local changes to commit."
fi

say "All checks passed ✅"
