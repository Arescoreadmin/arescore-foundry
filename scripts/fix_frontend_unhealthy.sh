#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
INFRA="$ROOT/infra"
FE_CONF="$ROOT/frontend/nginx.conf"
SEC="$INFRA/docker-compose.security.yml"

# 1) Correct Nginx conf (http-level map + temp paths under /tmp)
echo "==> Writing corrected frontend/nginx.conf"
cat > "$FE_CONF" <<'NGINX'
# Included inside 'http { ... }' by nginx.conf, so these are http-level directives.
limit_req_zone $binary_remote_addr zone=api_ratelimit:10m rate=10r/s;
map $http_upgrade $connection_upgrade { default upgrade; '' close; }

log_format json_combined escape=json
  '{'
  '"time":"$time_iso8601",'
  '"remote_addr":"$remote_addr",'
  '"request":"$request",'
  '"status":$status,'
  '"body_bytes_sent":$body_bytes_sent,'
  '"request_time":$request_time,'
  '"upstream_response_time":"$upstream_response_time",'
  '"upstream_status":"$upstream_status",'
  '"http_referer":"$http_referer",'
  '"http_user_agent":"$http_user_agent"'
  '}';

# Temp paths (so we can run read_only with tmpfs mounts)
client_body_temp_path /tmp/nginx-client-temp 1 2;
proxy_temp_path       /tmp/nginx-proxy-temp;
fastcgi_temp_path     /tmp/nginx-fastcgi-temp;
uwsgi_temp_path       /tmp/nginx-uwsgi-temp;
scgi_temp_path        /tmp/nginx-scgi-temp;

server {
  listen 8080;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  # Security headers (tune CSP for your app)
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy no-referrer-when-downgrade always;
  add_header X-XSS-Protection "1; mode=block" always;
  add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' data: blob:;" always;

  access_log /dev/stdout json_combined;
  error_log  /dev/stderr warn;

  sendfile on;
  tcp_nopush on;
  tcp_nodelay on;
  keepalive_timeout 65;

  gzip on;
  gzip_types text/plain text/css application/json application/javascript application/xml image/svg+xml;
  gzip_min_length 1024;

  location / { try_files $uri /index.html; }

  location = /ready {
    default_type application/json;
    return 200 "{\"ready\":true}";
  }

  location /api/ {
    limit_req zone=api_ratelimit burst=20 nodelay;

    proxy_pass http://orchestrator:8000/;
    proxy_http_version 1.1;

    # WebSockets
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;

    proxy_buffers 16 16k;
    proxy_buffer_size 16k;

    proxy_connect_timeout 1s;
    proxy_send_timeout    6s;
    proxy_read_timeout    6s;

    proxy_next_upstream error timeout http_502 http_503 http_504;
    proxy_next_upstream_tries 3;
  }
}
NGINX

# 2) Overwrite security override with valid YAML
echo "==> Writing known-good $SEC"
cat > "$SEC" <<'YML'
services:
  frontend:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
      - /var/cache/nginx
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]

  orchestrator:
    read_only: true
    tmpfs: [/tmp]
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]

  log_indexer:
    read_only: true
    tmpfs: [/tmp]
    security_opt:
      - no-new-privileges:true
    cap_drop: [ALL]
YML

# 3) Collect compose files (include any existing overrides)
FILES=(-f "$INFRA/docker-compose.yml")
[[ -f "$INFRA/docker-compose.override.yml" ]] && FILES+=(-f "$INFRA/docker-compose.override.yml")
[[ -f "$INFRA/docker-compose.health.yml"   ]] && FILES+=(-f "$INFRA/docker-compose.health.yml")
[[ -f "$INFRA/docker-compose.depends.yml"  ]] && FILES+=(-f "$INFRA/docker-compose.depends.yml")
FILES+=(-f "$SEC")

# 4) Validate combined compose (fail fast & show culprit)
echo "==> Validating compose config"
if ! docker compose "${FILES[@]}" config >/dev/null; then
  echo "Compose validation failed. Dumping combined config for debugging:"
  docker compose "${FILES[@]}" config
  exit 1
fi

# 5) Recreate frontend only; validate and reload nginx
echo "==> Recreate frontend"
docker compose "${FILES[@]}" up -d --build --force-recreate --no-deps frontend

echo "==> Validate nginx inside container"
docker compose "${FILES[@]}" exec -T frontend sh -lc 'nginx -t'

echo "==> Reload nginx (no restart)"
docker compose "${FILES[@]}" exec -T frontend sh -lc 'nginx -s reload || true'

# 6) Wait for healthy + probe
echo "==> Waiting for frontend to report (healthy)"
for i in {1..40}; do
  line="$(docker compose "${FILES[@]}" ps | awk '/frontend/ {print $0}')"
  echo "$line"
  echo "$line" | grep -q "(healthy)" && break
  sleep 1
done

echo "==> Probes"
curl -fsS http://localhost:3000/ready && echo
curl -fsS http://localhost:3000/api/ready && echo
