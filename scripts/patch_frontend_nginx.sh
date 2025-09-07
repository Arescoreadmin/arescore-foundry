#!/usr/bin/env bash
set -euo pipefail
usage(){ echo "usage: $0 {apply|revert}"; exit 2; }
[ $# -eq 1 ] || usage

ACTION="$1"
STACK_DIR="${STACK_DIR:-infra}"
SERVICE="${SERVICE:-frontend}"
CONF_IN_CONTAINER="/etc/nginx/conf.d/default.conf"
BACKUP_IN_CONTAINER="/etc/nginx/conf.d/default.conf.bak"

apply() {
  docker compose -f "$STACK_DIR/docker-compose.yml" up -d "$SERVICE" >/dev/null
  # ensure curl exists in the container (safe no-op if already present)
  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc 'command -v curl >/dev/null 2>&1 || (apk update >/dev/null 2>&1 && apk add --no-cache curl >/dev/null 2>&1)' || true

  # backup once
  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc "[ -f '$BACKUP_IN_CONTAINER' ] || cp '$CONF_IN_CONTAINER' '$BACKUP_IN_CONTAINER'"

  # inject robust /api/ proxy (timeouts + retries)
  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc "cat > $CONF_IN_CONTAINER" <<'NGINX'
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  # SPA route
  location / {
    try_files $uri /index.html;
  }

  # lightweight ready
  location = /ready {
    default_type application/json;
    return 200 "{\"ready\":true}";
  }

  # proxy to orchestrator with timeouts + retries
  location /api/ {
    proxy_pass http://orchestrator:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Connection "";
    proxy_redirect off;

    proxy_connect_timeout 1s;
    proxy_send_timeout    3s;
    proxy_read_timeout    3s;

    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 3;
  }
}
NGINX

  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc 'nginx -t && nginx -s reload'
  echo "✓ applied nginx frontend proxy patch"
}

revert() {
  # restore backup if present
  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc "[ -f '$BACKUP_IN_CONTAINER' ] && cp '$BACKUP_IN_CONTAINER' '$CONF_IN_CONTAINER' || true"
  docker compose -f "$STACK_DIR/docker-compose.yml" exec -T "$SERVICE" sh -lc 'nginx -t && nginx -s reload' || true
  echo "✓ reverted nginx frontend proxy patch (if backup existed)"
}

case "$ACTION" in
  apply)  apply  ;;
  revert) revert ;;
  *) usage ;;
esac
