#!/bin/bash
set -e

OVERRIDE_FILE="infra/docker-compose.override.yml"
BACKUP_FILE="${OVERRIDE_FILE}.bak.$(date +%Y%m%d-%H%M%S)"

echo "===== STEP 1: Backup existing override file ====="
cp "$OVERRIDE_FILE" "$BACKUP_FILE" || true

echo "===== STEP 2: Patch services to ensure infra_appnet (no duplicates) ====="
tmpfile=$(mktemp)
in_service=0
networks_present=0
infra_present=0

while IFS= read -r line || [ -n "$line" ]; do
    if [[ $line =~ ^[[:space:]]+[a-zA-Z0-9_-]+: ]] && [[ ! $line =~ services: ]]; then
        in_service=1
        networks_present=0
        infra_present=0
    fi

    if [[ $in_service -eq 1 && $line =~ ^[[:space:]]+networks: ]]; then
        networks_present=1
    fi

    if [[ $in_service -eq 1 && $line =~ infra_appnet ]]; then
        infra_present=1
    fi

    echo "$line" >> "$tmpfile"

    if [[ -z $line && $in_service -eq 1 ]]; then
        if [[ $infra_present -eq 0 ]]; then
            if [[ $networks_present -eq 0 ]]; then
                echo "    networks:" >> "$tmpfile"
            fi
            echo "      - infra_appnet" >> "$tmpfile"
        fi
        in_service=0
    fi
done < "$OVERRIDE_FILE"

mv "$tmpfile" "$OVERRIDE_FILE"

echo "===== STEP 3: Ensure infra_appnet in global networks block (no duplicate key) ====="
if grep -q "^networks:" "$OVERRIDE_FILE"; then
    if ! grep -q "infra_appnet:" "$OVERRIDE_FILE"; then
        sed -i '/^networks:/a\  infra_appnet:\n    external: true' "$OVERRIDE_FILE"
    fi
else
cat <<'EOF' >> "$OVERRIDE_FILE"

networks:
  infra_appnet:
    external: true
EOF
fi

echo "===== STEP 4: Normalize line endings ====="
sed -i 's/\r$//' "$OVERRIDE_FILE"

echo "===== STEP 5: Restart Docker stack ====="
docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  down
docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  up -d

echo "===== STEP 6: Check container health ====="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "===== PATCH & TEST COMPLETE ====="
echo "Backup saved to: $BACKUP_FILE"
