#!/bin/bash

NETWORK_NAME="infra_appnet"
SUBNET="10.2.0.0/16"
GATEWAY="10.2.0.1"

echo "🔧 Fixing Docker network: $NETWORK_NAME"

# Remove the broken network if it exists
if docker network inspect "$NETWORK_NAME" &>/dev/null; then
  echo "🧨 Removing existing network: $NETWORK_NAME"
  docker network rm "$NETWORK_NAME"
fi

# Recreate it with the correct labels
echo "🛠️ Recreating network with correct labels..."
docker network create "$NETWORK_NAME" \
  --driver bridge \
  --subnet "$SUBNET" \
  --gateway "$GATEWAY" \
  --label com.docker.compose.network="$NETWORK_NAME" \
  --label tier=infrastructure \
  --label environment=production

echo "✅ Network $NETWORK_NAME created"
