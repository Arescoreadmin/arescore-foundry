#!/bin/bash
# Usage: ./patch-compose-files.sh [network_name] (default: infra_appnet)

set -eo pipefail

# Configuration
NETWORK_NAME="${1:-infra_appnet}"
COMPOSE_FILES=(
  "infra/docker-compose.yml"
  "infra/docker-compose.prometheus.yml"
  "infra/docker-compose.override.yml"
)

# Backup original files
backup_files() {
  echo "Creating backups with .bak prefix..."
  for file in "${COMPOSE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
      cp -v "$file" "${file}.bak-$(date +%Y%m%d%H%M%S)"
    fi
  done
}

# Patch network configuration
patch_networks() {
  echo "Standardizing on network: $NETWORK_NAME"
  
  for file in "${COMPOSE_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
      echo "Warning: File $file not found"
      continue
    fi

    # 1. Remove version field
    sed -i '/^version:/d' "$file"

    # 2. Replace all network references
    sed -i \
      -e "s/\(appnet\|infra_appnet\|default\)/$NETWORK_NAME/g" \
      -e "s/networks:/networks:\n  $NETWORK_NAME:\n    name: $NETWORK_NAME\n    driver: bridge\n    attachable: true\n    labels:\n      tier: infrastructure\n      purpose: observability\n/g" \
      "$file"

    # 3. Ensure services use the standardized network
    if grep -q "services:" "$file"; then
      sed -i "/services:/,/^[^ ]/s/networks:/networks:\n      $NETWORK_NAME:/g" "$file"
    fi

    echo "Patched: $file"
  done
}

# Create the network with production settings
create_network() {
  if docker network inspect "$NETWORK_NAME" &>/dev/null; then
    echo "Network $NETWORK_NAME already exists"
  else
    echo "Creating production network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME" \
      --driver bridge \
      --label "env=production" \
      --label "tier=infrastructure" \
      --label "owner=devops" \
      -o "com.docker.network.bridge.enable_icc"="false"
  fi
}

# Main execution
main() {
  backup_files
  patch_networks
  create_network
  
  echo ""
  echo "Patch complete. To apply changes:"
  echo "  docker compose -p infra down"
  echo "  docker compose -p infra up -d"
  echo ""
  echo "Network details:"
  docker network inspect "$NETWORK_NAME" --format '{{json .Labels}}' | jq
}

main