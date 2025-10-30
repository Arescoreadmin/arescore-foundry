# scripts/fix_compose_sentinelcore.sh
#!/usr/bin/env bash
set -euo pipefail
F=infra/docker-compose.yml
[[ -f "$F" ]] || { echo "missing $F"; exit 2; }
cp -v "$F" "$F.bak.$(date +%s)"

awk '
  BEGIN{
    in_sc=0; in_dep=0; need_ports=0;
  }
  # enter sentinelcore service
  /^  sentinelcore:[[:space:]]*$/ { in_sc=1; in_dep=0 }
  # leave sentinelcore on next top-level service (two spaces + word + colon)
  in_sc && /^  [a-zA-Z0-9_.-]+:[[:space:]]*$/ && $0 !~ /^  sentinelcore:/ {
    # if we needed to insert ports and did not yet, inject before leaving
    if (need_ports) {
      print "    ports:"
      print "      - \"8000:8000\""
      need_ports=0
    }
    in_sc=0; in_dep=0
  }

  {
    if (in_sc) {
      # detect depends_on start/end inside sentinelcore
      if ($0 ~ /^[[:space:]]{4}depends_on:[[:space:]]*$/) { in_dep=1 }
      else if (in_dep && $0 ~ /^[[:space:]]{4}[a-zA-Z0-9_.-]+:[[:space:]]*$/) { in_dep=0 } # next 4-space key ends depends_on

      # if a wrongly nested ports: appears while inside depends_on, skip it and its immediate list items,
      # set flag to inject later at service level.
      if (in_dep && $0 ~ /^[[:space:]]{6,}ports:[[:space:]]*$/) {
        need_ports=1
        skip_list=1
        next
      }
      if (skip_list) {
        # consume list items under the bad ports (indented dashes)
        if ($0 ~ /^[[:space:]]{6,}-[[:space:]]/) { next } else { skip_list=0 }
      }
    }
    print
  }
  END{
    # if file ended inside sentinelcore and we still owe a ports block, append it
    if (in_sc && need_ports) {
      print "    ports:"
      print "      - \"8000:8000\""
    }
  }
' "$F" > "$F.tmp"

mv "$F.tmp" "$F"

# validate
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null && echo "✅ compose valid"
