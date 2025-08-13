#!/usr/bin/env bash
set -euo pipefail

# Colors
red(){ printf "[31m%s[0m
" "$*"; }
green(){ printf "[32m%s[0m
" "$*"; }
yellow(){ printf "[33m%s[0m
" "$*"; }

# Ports (override via env)
OBSERVER_PORT="${OBSERVER_PORT:-8070}"
RCA_PORT="${RCA_PORT:-8082}"
HARDEN_PORT="${HARDEN_PORT:-8083}"
ATTACK_PORT="${ATTACK_PORT:-8084}"

# JSON pretty printer: prefer jq, else Python, else raw
pp(){
  if command -v jq >/dev/null 2>&1; then jq .; 
  elif command -v python >/dev/null 2>&1; then python -m json.tool; 
  else cat; fi
}

check_http(){
  local name="$1" url="$2" expect="$3"
  local out
  if ! out="$(curl -sS --max-time 8 "$url" 2>&1)"; then
    red "✗ $name unreachable: $url"; echo "$out" | sed 's/^/  /'; return 1
  fi
  if [ -n "$expect" ] && ! printf '%s' "$out" | grep -q "$expect"; then
    yellow "~ $name responded but missing: $expect"; printf '%s
' "$out" | pp | sed 's/^/  /'
    return 1
  fi
  green "✓ $name OK"; printf '%s
' "$out" | pp >/dev/null
}

banner(){ printf "
==== %s ====
" "$*"; }

banner "Container status"
docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml ps || true

banner "Health endpoints"
check_http "observer_hub /health" "http://localhost:${OBSERVER_PORT}/health" '"ok": true' || true
check_http "rca_ai /health"       "http://localhost:${RCA_PORT}/health"       '"ok": true' || true
check_http "hardening_ai /health" "http://localhost:${HARDEN_PORT}/health"    '"ok": true' || true
check_http "attack_driver /health" "http://localhost:${ATTACK_PORT}/health"   '"ok": true' || true

banner "Functional endpoints"
check_http "observer_hub /status" "http://localhost:${OBSERVER_PORT}/status" '{' || true
check_http "observer_hub /risks"  "http://localhost:${OBSERVER_PORT}/risks"  '{' || true

# RCA diagnose
if curl -sS -X POST "http://localhost:${RCA_PORT}/diagnose" -o /tmp/rca.json; then
  green "✓ rca_ai /diagnose OK"; cat /tmp/rca.json | pp >/dev/null
else
  yellow "~ rca_ai /diagnose call failed"
fi

# Attack driver
if curl -sS -X POST "http://localhost:${ATTACK_PORT}/run" \
  -H 'Content-Type: application/json' -d '{"mode":"recon"}' -o /tmp/attack.json; then
  green "✓ attack_driver /run OK"; cat /tmp/attack.json | pp >/dev/null
else
  yellow "~ attack_driver /run call failed"
fi

echo
green "Test run complete."