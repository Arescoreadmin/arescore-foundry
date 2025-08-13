#!/usr/bin/env bash
set -euo pipefail

# --- Config
OVERRIDE="infra/docker-compose.override.yml"
COMPOSE="docker compose -f infra/docker-compose.yml -f ${OVERRIDE}"
TS="$(date +%Y%m%d-%H%M%S)"

# --- Helpers
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
red(){ printf "\033[31m%s\033[0m\n" "$*"; }

add_health_route_py() {
  local file="$1"
  if [ ! -f "$file" ]; then yellow "  ~ Skipping (missing): $file"; return; fi
  if grep -qE '@app\.get\(\"/health\"\)' "$file"; then
    green "  ✓ Health route already present: $file"
  else
    cat >> "$file" <<'PYEOF'

@app.get("/health")
async def health():
    return {"ok": True}
PYEOF
    green "  ✓ Added /health to: $file"
  fi
}

# --- 1) Patch Python apps (idempotent)
echo ">> Patching Python services with /health endpoints…"
add_health_route_py "backend/observer_hub/app.py"
add_health_route_py "backend/rca_ai/app.py"
add_health_route_py "backend/hardening_ai/app.py"
add_health_route_py "backend/attack_driver/driver.py"

# --- 2) Patch docker-compose.override.yml with healthchecks (in-place)
echo ">> Patching ${OVERRIDE} with Docker healthchecks…"

if [ ! -f "${OVERRIDE}" ]; then
  red "  ✗ ${OVERRIDE} not found. Aborting."; exit 1
fi

cp -f "${OVERRIDE}" "${OVERRIDE}.bak-${TS}"

# Remove any deprecated top-level version key
sed -i.bak '/^version:/d' "${OVERRIDE}"

insert_healthcheck_block () {
  local service="$1" port="$2"
  local pattern="^[[:space:]]*${service}:[[:space:]]*$"
  # If a healthcheck already exists for this service, skip
  if awk "/${pattern}/, /^[^[:space:]]/ { if(/healthcheck:/){found=1} } END{exit (found?0:1)}" "${OVERRIDE}"; then
    green "  ✓ ${service}: healthcheck already present"
    return
  fi
  # Insert healthcheck after the first 'restart:' or 'ports:' or env block under this service
  awk -v svc="${service}" -v port="${port}" '
    BEGIN{in_s=0; inserted=0}
    {
      print $0
      if ($0 ~ "^[[:space:]]*"svc":[[:space:]]*$") { in_s=1 }
      else if (in_s==1 && $0 ~ "^[^[:space:]]"){ in_s=0 }  # next service or top-level
      if (in_s==1 && inserted==0 && ($0 ~ /^[[:space:]]*restart:/ || $0 ~ /^[[:space:]]*ports:/ || $0 ~ /^[[:space:]]*volumes:/ || $0 ~ /^[[:space:]]*environment:/)) {
        # defer actual insert until we see the next non-indented or next sibling key at same indentation
      }
    }
    in_s==1 && inserted==0 && $0 ~ /^[[:space:]]*restart:/ {
      # Insert healthcheck right after restart:
      print "      healthcheck:"
      print "        test: [\"CMD\", \"wget\", \"-qO-\", \"http://localhost:" port "/health\"]"
      print "        interval: 15s"
      print "        timeout: 5s"
      print "        retries: 5"
      print "        start_period: 10s"
      inserted=1
    }
    ' "${OVERRIDE}" > "${OVERRIDE}.tmp1"

  # If not inserted yet, try after ports:
  if ! diff -q "${OVERRIDE}" "${OVERRIDE}.tmp1" >/dev/null 2>&1; then
    mv "${OVERRIDE}.tmp1" "${OVERRIDE}"
  else
    awk -v svc="${service}" -v port="${port}" '
      BEGIN{in_s=0; inserted=0}
      {
        print $0
        if ($0 ~ "^[[:space:]]*"svc":[[:space:]]*$") { in_s=1 }
        else if (in_s==1 && $0 ~ "^[^[:space:]]"){ in_s=0 }
      }
      in_s==1 && inserted==0 && $0 ~ /^[[:space:]]*ports:/ {
        print "      healthcheck:"
        print "        test: [\"CMD\", \"wget\", \"-qO-\", \"http://localhost:" port "/health\"]"
        print "        interval: 15s"
        print "        timeout: 5s"
        print "        retries: 5"
        print "        start_period: 10s"
        inserted=1
      }
    ' "${OVERRIDE}" > "${OVERRIDE}.tmp2"
    if ! diff -q "${OVERRIDE}" "${OVERRIDE}.tmp2" >/dev/null 2>&1; then
      mv "${OVERRIDE}.tmp2" "${OVERRIDE}"
    else
      # As a last resort, append under the service block end by re-rendering (simpler: append a comment section)
      printf "\n# healthcheck for %s (appended by patch script)\n# If needed, move under the %s service block manually.\n" "${service}" "${service}" >> "${OVERRIDE}"
      printf "# test: [\"CMD\", \"wget\", \"-qO-\", \"http://localhost:%s/health\"]\n\n" "${port}" >> "${OVERRIDE}"
      yellow "  ~ Could not place healthcheck neatly under ${service}; appended guidance comment at end."
      rm -f "${OVERRIDE}.tmp2" 2>/dev/null || true
    fi
  fi
}

# Ensure restart policy exists; add if missing for our services
ensure_restart_policy () {
  local service="$1"
  if awk "/^[[:space:]]*${service}:[[:space:]]*$/,/^[^[:space:]]/ { if(/^[[:space:]]*restart:/){found=1} } END{exit (found?0:1)}" "${OVERRIDE}"; then
    : # present
  else
    # Insert restart: unless-stopped right after container_name or build line
    awk -v svc="${service}" '
      BEGIN{in_s=0; inserted=0}
      {
        print $0
        if ($0 ~ "^[[:space:]]*"svc":[[:space:]]*$") { in_s=1 }
        else if (in_s==1 && $0 ~ "^[^[:space:]]"){ in_s=0 }
        if (in_s==1 && inserted==0 && $0 ~ /^[[:space:]]*(container_name|build):/){
          print "    restart: unless-stopped"
          inserted=1
        }
      }
    ' "${OVERRIDE}" > "${OVERRIDE}.tmp3" && mv "${OVERRIDE}.tmp3" "${OVERRIDE}"
  fi
}

# Apply restart + healthcheck per service
for svc in observer_hub:8070 rca_ai:8082 hardening_ai:8083 attack_driver:8084; do
  name="${svc%%:*}"; port="${svc##*:}"
  ensure_restart_policy "${name}"
  insert_healthcheck_block "${name}" "${port}"
done

green "  ✓ Patched ${OVERRIDE} (backup: ${OVERRIDE}.bak-${TS})"

# --- 3) Rebuild & restart changed services
echo ">> Rebuilding images (only changed)…"
${COMPOSE} build observer_hub rca_ai hardening_ai attack_driver

echo ">> Restarting services…"
${COMPOSE} up -d observer_hub rca_ai hardening_ai attack_driver

# --- 4) Verify
echo ">> Verifying health endpoints…"
check() {
  local name="$1" url="$2"
  if curl -fsS --max-time 8 "$url" >/dev/null; then
    green "  ✓ $name healthy"
  else
    red "  ✗ $name failed: $url"
  fi
}
check "observer_hub" "http://localhost:8070/health"
check "rca_ai"       "http://localhost:8082/health"
check "hardening_ai" "http://localhost:8083/health"
check "attack_driver" "http://localhost:8084/health"

echo ">> Done."
