set -euo pipefail
test -f infra/.env || { echo "infra/.env missing"; exit 1; }
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null
