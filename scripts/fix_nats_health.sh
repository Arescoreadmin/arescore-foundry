#!/usr/bin/env bash
set -euo pipefail

patch_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local bak="${f}.bak.$(date +%s)"
  cp "$f" "$bak"

  # 1) Drop the obsolete top-level version: line
  sed -i -E '1,10{s/^[[:space:]]*version:[[:space:]]*".*"\s*$//}' "$f"

  # 2) Ensure nats uses an Alpine tag, enable monitoring, and add a real healthcheck
  #    - force image: nats:2.10-alpine (or keep existing if already alpine)
  #    - command: -js -sd /data -m 8222
  #    - healthcheck via wget to /healthz (BusyBox wget exists on Alpine)
  awk '
    BEGIN{in_nats=0; printed_cmd=0; printed_hc=0; printed_ports=0}
    {
      if ($0 ~ /^[[:space:]]*nats:[[:space:]]*$/) {in_nats=1; printed_cmd=0; printed_hc=0; printed_ports=0; print; next}
      if (in_nats && $0 ~ /^[[:space:]]*[a-zA-Z0-9_-]+:[[:space:]]*$/) {in_nats=0}
      if (in_nats && $0 ~ /^[[:space:]]*image:/) {
        print gensub(/image:.*/, "image: nats:2.10-alpine", 1)
        next
      }
      if (in_nats && $0 ~ /^[[:space:]]*command:/) next
      if (in_nats && $0 ~ /^[[:space:]]*healthcheck:/) next
      if (in_nats && $0 ~ /^[[:space:]]*ports:/) {printed_ports=1}
      print
      if (in_nats && $0 ~ /^[[:space:]]*image:[[:space:]]*nats.*$/ && printed_cmd==0) {
        print "    command: [\"-js\",\"-sd\",\"/data\",\"-m\",\"8222\"]"
        printed_cmd=1
      }
      if (in_nats && printed_hc==0 && printed_cmd==1) {
        print "    healthcheck:"
        print "      test: [\"CMD-SHELL\", \"wget -qO- http://127.0.0.1:8222/healthz | grep -q ok\"]"
        print "      interval: 5s"
        print "      timeout: 3s"
        print "      retries: 20"
        print "      start_period: 10s"
        printed_hc=1
      }
      # Optional but handy: expose the monitor port to host for debugging in CI logs
      if (in_nats && printed_ports==0 && $0 ~ /^[[:space:]]*volumes:/) {
        print "    ports:"
        print "      - \"4222:4222\""  # client"
        print "      - \"8222:8222\""  # monitor"
        printed_ports=1
      }
    }
  ' "$f" > "$f.tmp"

  mv "$f.tmp" "$f"
  echo "Patched $f (backup at $bak)"
}

patch_file compose.yml
patch_file compose.federated.yml || true

# If your services depend on 'service_healthy', make sure they actually wait on NATS
# This turns 'depends_on: nats' into a health-based dependency where present.
for f in compose.yml compose.federated.yml; do
  [[ -f "$f" ]] || continue
  # crude but effective: replace plain depends_on entries for nats with condition: service_healthy
  perl -0777 -pe '
    s/(depends_on:\s*\n(\s*-\s*nats\s*\n)+)/"depends_on:\n  nats:\n    condition: service_healthy\n"/eg
  ' -i "$f" || true
done
