#!/usr/bin/env bash
set -Eeuo pipefail
trap 'ec=$?; echo; echo "Ì≤• Exit $ec at line $LINENO"; echo; echo "==> compose ps"; docker compose "${DC[@]}" ps || true; echo; echo "==> tail logs"; docker compose "${DC[@]}" logs --tail=120 || true; exit $ec' ERR

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

ROOT="$(pwd)"
INFRA="$ROOT/infra"

# Build compose args from files that actually exist
DC=(-f "$INFRA/docker-compose.yml")
for f in docker-compose.override.yml docker-compose.health.yml docker-compose.depends.yml docker-compose.security.yml; do
  [[ -f "$INFRA/$f" ]] && DC+=(-f "$INFRA/$f")
done

compose(){ docker compose "${DC[@]}" "$@"; }

health_of(){
  local svc="$1" id status
  id="$(compose ps -q "$svc" | tr -d '\r' || true)"
  [[ -n "$id" ]] || { echo "none"; return; }
  status="$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo "none")"
  echo "$status"
}

wait_health(){
  local timeout="${1:-240}" start="$SECONDS"
  say "Waiting for health (timeout ${timeout}s)"
  while (( SECONDS - start < timeout )); do
    compose ps || true
    local ok=1
    [[ "$(health_of frontend)"     == "healthy" ]] || ok=0
    [[ "$(health_of orchestrator)" == "healthy" ]] || ok=0
    if compose ps | grep -q log_indexer; then
      st="$(health_of log_indexer)"
      if [[ "$st" != "none" && "$st" != "healthy" ]]; then ok=0; fi
    fi
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

say "Up (build) with best effort wait"
if docker compose version 2>/dev/null | grep -qE 'v2\.(2[0-9]|[3-9][0-9])'; then
  if ! compose up -d --build --wait --wait-timeout 120; then
    echo "compose --wait failed; falling back to manual wait"
    compose up -d --build
  fi
else
  compose up -d --build
fi

wait_health 300 || { echo "‚ö†Ô∏è Still not healthy after timeout"; exit 2; }

say "Probes"
curl -fsS http://localhost:3000/ready && echo "OK /ready"
curl -fsS http://localhost:3000/api/ready && echo "OK /api/ready"

say "Summary"
echo "frontend:     $(health_of frontend)"
echo "orchestrator: $(health_of orchestrator)"
if compose ps | grep -q log_indexer; then echo "log_indexer:  $(health_of log_indexer)"; fi

say "Git changes"
git status --porcelain || true

# Optional: commit if there are changes
if git status --porcelain | grep -q .; then
  BRANCH="${BRANCH:-codex/frontend-hardening}"
  say "Committing changes to $BRANCH"
  git checkout -B "$BRANCH"
  git add -A
  git commit -m "infra: finalize nginx hardening + health/depends/security; smoke verified"
  git push -u origin "$BRANCH" || true
  echo "Create PR when ready (or use: gh pr create ...)."
else
  echo "No local changes to commit."
fi

say "Done ‚úÖ"
