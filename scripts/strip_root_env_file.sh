#!/usr/bin/env bash
set -euo pipefail
FILE="compose.yml"

echo "==> Backing up $FILE"
cp "$FILE" "$FILE.bak.$(date +%s)"

echo "==> Removing illegal top-level env_file from $FILE (if present)"
awk '
BEGIN{skip=0}
# Start skipping when we see a top-level "env_file:" (no indent)
(/^env_file:[[:space:]]*$/ && $0 !~ /^[[:space:]]+/){skip=1; next}
# Stop skipping when we hit the next top-level key (no indent) or EOF
(skip && $0 !~ /^[[:space:]]+/){skip=0}
# While skipping indented lines under env_file list
(skip && /^[[:space:]]+/){next}
# Default: print line
{print}
' "$FILE" > "$FILE.tmp"

mv "$FILE.tmp" "$FILE"
echo "==> Validating merged config"
docker compose -f compose.yml -f compose.federated.yml config >/dev/null && echo "OK: compose parses"
