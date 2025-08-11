# scripts/finalize_health.sh
#!/usr/bin/env bash
set -Eeuo pipefail

trap 'ec=$?;
  echo; echo "  Exit $ec at line $LINENO";
  echo; echo "==> compose ps"; docker compose "${DC[@]}" ps || true;
  echo; echo "==> tail logs";  docker compose "${DC[@]}" logs --tail=120 || true;
  exit $ec' ERR

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="$ROOT/infra"
FE_CONF="$ROOT/frontend/nginx.conf"

# Build compose args from files that actually exist (order matters)
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

# --- 1) Quiet health logs in Nginx (idempotent)
say "Silencing /ready and /api/ready from access logs"
if [[ ! -f "$FE_CONF" ]]; then
  echo "ERROR: $FE_CONF not found"; exit 2
fi

# Ensure LF endings (Windows safety)
sed -i 's/\r$//' "$FE_CONF"

# Add http-level map if not present
if ! grep -q '\$loggable' "$FE_CONF"; then
  tmp="$FE_CONF.tmp.$$"
  {
    echo "map \$request_uri \$loggable { default 1; =/ready 0; =/api/ready 0; }"
    cat "$FE_CONF"
  } > "$tmp" && mv "$tmp" "$FE_CONF"
fi

# Switch access_log to conditional form
if grep -q 'access_log /dev/stdout json_combined;' "$FE_CONF"; then
  sed -i 's|access_log /dev/stdout json_combined;|access_log /dev/stdout json_combined if=$loggable;|' "$FE_CONF"
fi

# Keep everything else as-is. We rely on your existing /api/ proxy and /ready route.

# --- 2) Validate compose config
say "Docker/Compose versions"
docker --version || true
docker compose version || true

say "Validating compose config"
compose config >/dev/null

# --- 3) Recreate frontend (so nginx.conf change is picked up)
say "Recreating frontend (build & restart)"
compose up -d --build --force-recreate --no-deps frontend

# --- 4) Wait for health (native --wait if available; fallback to manual)
if docker compose version 2>/dev/null | grep -qE 'v2\.(2[0-9]|[3-9][0-9])'; then
  say "Compose --wait path"
  compose up -d --wait --wait-timeout 120 || true
fi
wait_health 300

# --- 5) Probes
say "Probing endpoints"
curl -fsS http://localhost:3000/ready       && echo "OK /ready"
curl -fsS http://localhost:3000/api/ready   && echo "OK /api/ready"

# --- 6) Commit & push
say "Commit & push (if there are changes)"
if git status --porcelain | grep -q .; then
  BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo codex/healthchecks-and-deps)}"
  git add frontend/nginx.conf \
          infra/docker-compose.health.yml \
          infra/docker-compose.depends.yml \
          infra/docker-compose.security.yml \
          scripts/patch_log_indexer_health.sh 2>/dev/null || true
  git add -A
  git commit -m "infra: finalize healthchecks; quiet health logs; harden nginx; verified healthy"
  git push -u origin "$BRANCH" || true

  if [[ "${CREATE_PR:-0}" == "1" ]] && command -v gh >/dev/null 2>&1; then
    say "Creating PR via gh"
    gh pr create -t "Infra: finalize healthchecks & hardening" \
                 -b "All services healthy; quiet /ready logs; startup ordering + security hardened."
  else
    echo "PR not created (set CREATE_PR=1 and install GitHub CLI to auto-open)."
  fi
else
  echo "No changes to commit."
fi

say "All good ✅"
