# scripts/repair_compose_sentinelcore.sh
#!/usr/bin/env bash
set -euo pipefail
F=infra/docker-compose.yml
[[ -f "$F" ]] || { echo "missing $F"; exit 2; }
cp -v "$F" "$F.bak.$(date +%s)"

awk '
  BEGIN{
    in_sc=0; in_dep=0; skip_list=0; need_ports=0; printed_ports=0;
  }

  # enter sentinelcore
  /^  sentinelcore:[[:space:]]*$/ { in_sc=1; in_dep=0; skip_list=0; need_ports=0; printed_ports=0 }

  # leaving sentinelcore when a new top-level service appears
  in_sc && /^  [a-zA-Z0-9_.-]+:[[:space:]]*$/ && $0 !~ /^  sentinelcore:/ {
    if (need_ports && !printed_ports) {
      print "    ports:"
      print "      - \"8000:8000\""
    }
    in_sc=0; in_dep=0; skip_list=0; need_ports=0; printed_ports=0
  }

  {
    if (in_sc) {
      # detect a correct ports at service level (4 spaces)
      if ($0 ~ /^[[:space:]]{4}ports:[[:space:]]*$/) { printed_ports=1 }

      # depends_on boundaries (4-space key)
      if ($0 ~ /^[[:space:]]{4}depends_on:[[:space:]]*$/) { in_dep=1 }
      else if (in_dep && $0 ~ /^[[:space:]]{4}[a-zA-Z0-9_.-]+:[[:space:]]*$/) { in_dep=0 }

      # if a wrongly nested ports appears under depends_on, drop it & its list items
      if (in_dep && $0 ~ /^[[:space:]]{10}ports:[[:space:]]*$/) { skip_list=1; need_ports=1; next }
      if (skip_list) {
        if ($0 ~ /^[[:space:]]{10}-[[:space:]]/) { next } else { skip_list=0 }
      }
    }
    print
  }

  END{
    # file ended inside sentinelcore
    if (in_sc && need_ports && !printed_ports) {
      print "    ports:"
      print "      - \"8000:8000\""
    }
  }
' "$F" > "$F.tmp" && mv "$F.tmp" "$F"

# sanity: show the critical window
nl -ba "$F" | sed -n "60,90p"

# validate both files together
docker compose -f infra/docker-compose.yml -f infra/compose.opa.yml config >/dev/null && echo "✅ compose valid"
