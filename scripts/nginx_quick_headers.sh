#!/usr/bin/env bash
set -euo pipefail

# Adds safe, useful headers/caching to frontend/nginx.conf (server{} only).
# Idempotent: skips if the bits already exist.
# Usage:
#   bash scripts/nginx_quick_headers.sh
#   RESTART=1 bash scripts/nginx_quick_headers.sh     # also recreate frontend

ROOT="${ROOT:-$(pwd)}"
CONF="${CONF:-$ROOT/frontend/nginx.conf}"
BACKUP="${CONF}.bak.$(date +%Y%m%d-%H%M%S)"
RESTART="${RESTART:-0}"

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

[[ -f "$CONF" ]] || { echo "nginx.conf not found at $CONF"; exit 1; }

# Normalize line endings (Windows-safe)
sed -i 's/\r$//' "$CONF"

cp -a "$CONF" "$BACKUP"
say "Backup saved: $BACKUP"

need_header=0
need_index=0
need_static=0

grep -q 'add_header[[:space:]]\+X-Request-Id' "$CONF" || need_header=1
grep -q 'location[[:space:]]*=\s*/index\.html' "$CONF" || need_index=1
grep -q 'location[[:space:]]*~\*.*\.\(css\|js\|png\|jpg\|jpeg\|gif\|svg\|webp\|ico\|woff2\)\$' "$CONF" || need_static=1

if (( need_header )); then
  say "Adding: add_header X-Request-Id ..."
  # place near other security headers if present; otherwise after 'index index.html;'
  if grep -n 'add_header[[:space:]]\+X-XSS-Protection' "$CONF" >/dev/null; then
    sed -i '/add_header[[:space:]]\+X-XSS-Protection/a \  add_header X-Request-Id $request_id always;' "$CONF"
  else
    sed -i '/index[[:space:]]\+index\.html;/a \  add_header X-Request-Id $request_id always;' "$CONF"
  fi
else
  say "Header already present: X-Request-Id"
fi

if (( need_index || need_static )); then
  say "Adding index no-store and/or static immutable blocks..."
  awk -v add_index="$need_index" -v add_static="$need_static" '
    BEGIN{ printed_idx=0; printed_static=0 }
    # Before the first generic "location / {" block, inject our extras (if needed)
    $0 ~ /^[[:space:]]*location[[:space:]]*\/[[:space:]]*\{/ {
      if (add_index=="1" && printed_idx==0) {
        print "  # Ensure no-store for the app shell"
        print "  location = /index.html {"
        print "    add_header Cache-Control \"no-store\" always;"
        print "    try_files \\$uri =404;"
        print "  }"
        print ""
        printed_idx=1
      }
      if (add_static=="1" && printed_static==0) {
        print "  # Cache immutable for static assets (hashed filenames)"
        print "  location ~* \\\\.(css|js|png|jpg|jpeg|gif|svg|webp|ico|woff2?)$ {"
        print "    expires 30d;"
        print "    add_header Cache-Control \"public, immutable\";"
        print "    try_files \\$uri =404;"
        print "  }"
        print ""
        printed_static=1
      }
      print $0
      next
    }
    { print $0 }
    END{
      # If we never saw a "location / {", append at end of server block (best effort)
      if ((add_index=="1" && printed_idx==0) || (add_static=="1" && printed_static==0)) {
        print ""
        if (add_index=="1" && printed_idx==0) {
          print "  # Ensure no-store for the app shell"
          print "  location = /index.html {"
          print "    add_header Cache-Control \"no-store\" always;"
          print "    try_files \\$uri =404;"
          print "  }"
          print ""
        }
        if (add_static=="1" && printed_static==0) {
          print "  # Cache immutable for static assets (hashed filenames)"
          print "  location ~* \\\\.(css|js|png|jpg|jpeg|gif|svg|webp|ico|woff2?)$ {"
          print "    expires 30d;"
          print "    add_header Cache-Control \"public, immutable\";"
          print "    try_files \\$uri =404;"
          print "  }"
          print ""
        }
      }
    }
  ' "$CONF" > "$CONF.tmp" && mv "$CONF.tmp" "$CONF"
else
  say "Index/static blocks already present"
fi

say "Done patching: $CONF"

if (( RESTART )); then
  say "Recreating frontend container"
  INFRA="$ROOT/infra"
  DC=(-f "$INFRA/docker-compose.yml")
  for f in docker-compose.override.yml docker-compose.health.yml docker-compose.depends.yml docker-compose.security.yml docker-compose.nginxbind.yml; do
    [[ -f "$INFRA/$f" ]] && DC+=(-f "$INFRA/$f")
  done
  docker compose "${DC[@]}" up -d --force-recreate --no-deps frontend
  say "Probe:"
  curl -fsS http://localhost:3000/ready >/dev/null && echo "  /ready OK"
fi

say "Tip: commit your changes"
