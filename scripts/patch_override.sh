#!/usr/bin/env bash
set -e

FILE="infra/docker-compose.override.yml"
BACKUP="${FILE}.bak.$(date +%Y%m%d%H%M%S)"

echo "📦 Backing up $FILE to $BACKUP"
cp "$FILE" "$BACKUP"

echo "🛠  Patching $FILE..."
# Remove all container_name lines (with any indentation)
sed -i.bak '/^[[:space:]]*container_name:/d' "$FILE"

# Add 'networks: [appnet]' after the ports/env/restart/healthcheck block for each service
# This assumes 'services:' indentation is 2 spaces, and service props are indented 4 spaces
awk '
  /^[[:space:]]{2}[^[:space:]]/ { in_service=1 } # matches a service name line
  in_service && /^[[:space:]]{2}[^[:space:]]+:/ { service_name=$0 }
  /^[[:space:]]{4}restart:/ { print; print "    networks: [appnet]"; next }
  { print }
' "$FILE" > "${FILE}.tmp" && mv "${FILE}.tmp" "$FILE"

echo "✅ Patch complete."
echo "   - container_name lines removed"
echo "   - networks: [appnet] added after restart: in each service"

echo "💡 If some services don’t have a 'restart:' line, you’ll need to insert 'networks: [appnet]' manually under them."
