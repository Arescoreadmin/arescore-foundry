#!/bin/bash
set -e

NETWORK_NAME="foundry_net"
COMPOSE_FILES=$(find ./infra ./infra-backup-20250812 -type f -name 'docker-compose*.yml')

echo "🔧 Patching Docker Compose files to add external network: $NETWORK_NAME"

for file in $COMPOSE_FILES; do
  echo "📄 Editing: $file"

  # Skip files already patched
  if grep -q "$NETWORK_NAME" "$file"; then
    echo "  🔁 Already patched. Skipping."
    continue
  fi

  # Inject network into all service blocks
  awk -v net="$NETWORK_NAME" '
    BEGIN { in_services=0 }
    /^services:/ { in_services=1; print; next }
    in_services && /^[^[:space:]]/ { in_services=0 } # end of services block

    in_services && /^[[:space:]]+[a-zA-Z0-9_-]+:$/ {
      service_name_line = $0
      getline next_line
      print service_name_line
      print next_line
      print "    networks:"
      print "      - " net
      next
    }

    { print }
  ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  # Add global networks section if missing
  if ! grep -q "^networks:" "$file"; then
    cat <<EOF >> "$file"

networks:
  $NETWORK_NAME:
    external: true
EOF
  fi

  echo "  ✅ Patched $file"
done

# Create Docker network if it doesn't exist
if ! docker network ls | grep -q "$NETWORK_NAME"; then
  echo "➕ Creating Docker network '$NETWORK_NAME'"
  docker network create --driver bridge "$NETWORK_NAME"
else
  echo "✅ Docker network '$NETWORK_NAME' already exists"
fi

echo "✅ All docker-compose files patched successfully."
