# scripts/repair_opa_override.sh
#!/usr/bin/env bash
set -euo pipefail

F="infra/compose.opa.yml"
mkdir -p infra
cp -v "$F" "$F.bak.$(date +%s)" 2>/dev/null || true

cat > "$F" <<'YML'
services:
  opa:
    image: openpolicyagent/opa:0.67.0
    command: ["run","--server","--log-level=info","/policies"]
    volumes:
      - ../policies:/policies:ro
    ports:
      - "8181:8181"
    read_only: true
    cap_drop: ["ALL"]
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
    healthcheck:
      test: ["CMD","wget","-qO-","http://127.0.0.1:8181/health"]
      interval: 15s
      timeout: 5s
      retries: 10
      start_period: 15s
YML

# sanity
docker compose -f infra/docker-compose.yml -f "$F" config >/dev/null
echo "✅ OPA override repaired & valid"
