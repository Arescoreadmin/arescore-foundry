#!/usr/bin/env bash
set -euo pipefail

OVERRIDE_FILE="infra/docker-compose.override.yml"

echo "----- Backing up current override file -----"
cp "$OVERRIDE_FILE" "${OVERRIDE_FILE}.bak-$(date +%Y%m%d-%H%M%S)" || {
    echo "No existing override file found, skipping backup."
}

echo "----- Patching services to use infra_appnet -----"
# Add `networks: - infra_appnet` to any service missing it
awk '
  BEGIN { in_service=0 }
  /^services:/ { print; next }
  /^[^[:space:]]/ { in_service=0 }  # reset on new top-level
  /^[[:space:]]+[a-zA-Z0-9_-]+:$/ { in_service=1; print; next }
  {
    if (in_service && $0 ~ /^[[:space:]]+networks:/) {
      in_service=0
    }
    if (in_service && $0 ~ /^[[:space:]]+restart:/) {
      print $0
      print "    networks:"
      print "      - infra_appnet"
      in_service=0
      next
    }
    print
  }
' "$OVERRIDE_FILE" > "${OVERRIDE_FILE}.tmp" && mv "${OVERRIDE_FILE}.tmp" "$OVERRIDE_FILE"

echo "----- Appending networks block if missing -----"
if ! grep -q '^networks:' "$OVERRIDE_FILE"; then
    cat <<'YAML' >> "$OVERRIDE_FILE"

networks:
  infra_appnet:
    external: true
YAML
fi

echo "----- Ensuring external: true for infra_appnet -----"
# Force the networks block to have external:true
awk '
  BEGIN {networks_section=0}
  /^networks:/ {networks_section=1; print; next}
  /^[^[:space:]]/ {networks_section=0; print; next}
  {
    if (networks_section && $0 ~ /^  infra_appnet:/) {
      print $0
      getline
      if ($0 !~ /external:/) {
        print "    external: true"
      } else {
        print $0
      }
      next
    }
    print
  }
' "$OVERRIDE_FILE" > "${OVERRIDE_FILE}.tmp" && mv "${OVERRIDE_FILE}.tmp" "$OVERRIDE_FILE"

echo "----- Normalizing line endings -----"
sed -i 's/\r$//' "$OVERRIDE_FILE"

echo "----- Patch complete! Restarting stack -----"
docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  down || true

docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  up -d

echo "----- Stack restarted. Run ./scripts/diagnose_stack.sh to verify -----"
