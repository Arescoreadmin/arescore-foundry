#!/usr/bin/env bash
set -euo pipefail
FILE="compose.yml"
BACKUP="compose.yml.bak.$(date +%s)"

cp "$FILE" "$BACKUP"

# if service 'nats' already has command/healthcheck, replace; otherwise insert sensible defaults
awk '
  BEGIN{in_nats=0}
  /^services:/ {print; next}
  {
    if ($0 ~ /^[[:space:]]*nats:[[:space:]]*$/) {in_nats=1; print; next}
    if (in_nats) {
      # stop block when next top-level service key begins
      if ($0 ~ /^[[:space:]]*[a-zA-Z0-9_-]+:[[:space:]]*$/) {in_nats=0}
    }
    if (in_nats && $0 ~ /^[[:space:]]*command:/) next
    if (in_nats && $0 ~ /^[[:space:]]*healthcheck:/) next
    print
    if (in_nats && $0 ~ /^[[:space:]]*image:[[:space:]]*nats/) {
      print "    command: [\"-js\",\"-sd\",\"/data\",\"-m\",\"8222\"]"
      print "    healthcheck:"
      print "      test: [\"CMD-SHELL\", \"(wget -qO- http://127.0.0.1:8222/healthz 2>/dev/null | grep -q ok) || nc -z 127.0.0.1 4222\"]"
      print "      interval: 5s"
      print "      timeout: 2s"
      print "      retries: 12"
      print "      start_period: 5s"
    }
  }
' "$FILE" > "${FILE}.tmp"

mv "${FILE}.tmp" "$FILE"
echo "Patched $FILE (backup at $BACKUP)"
