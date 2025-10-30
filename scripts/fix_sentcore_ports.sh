# scripts/fix_sentcore_ports.sh
#!/usr/bin/env bash
set -euo pipefail
F=infra/docker-compose.yml
cp -v "$F" "$F.bak.$(date +%s)"

# Dedent the misplaced ports block inside sentinelcore (only within that service block)
awk '
  BEGIN{in_sc=0}
  # enter sentinelcore block
  /^  sentinelcore:\s*$/ {in_sc=1}
  # leave on next top-level service
  in_sc && /^  [a-zA-Z0-9_.-]+:\s*$/ && $0 !~ /^  sentinelcore:/ {in_sc=0}

  {
    if (in_sc) {
      # fix a wrongly nested "ports:" (10 spaces -> 4 spaces)
      if ($0 ~ /^\s{10}ports:\s*$/) { sub(/^\s{10}ports:/,"    ports:") }
      # fix the list item under ports (8 spaces -> 6 spaces)
      if ($0 ~ /^\s{8}-\s*\"8000:8000\"/) { sub(/^\s{8}-/,"      -") }
    }
    print
  }
' "$F" > "$F.tmp" && mv "$F.tmp" "$F"

# Validate
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null && echo "✅ compose valid"
