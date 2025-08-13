#!/usr/bin/env bash
set -euo pipefail

PROJ=infra
STACK_FILES=(
  infra/docker-compose.yml
  infra/docker-compose.prometheus.yml
  infra/docker-compose.override.yml
)

OUTDIR="diagnostics"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="${OUTDIR}/report-${TS}.txt"
JSON="${OUTDIR}/report-${TS}.json"
mkdir -p "$OUTDIR"

ok(){ echo -e "✅ $*" | tee -a "$OUT"; }
warn(){ echo -e "🟡 $*" | tee -a "$OUT"; }
err(){ echo -e "❌ $*" | tee -a "$OUT"; }
sep(){ echo -e "\n----- $* -----" | tee -a "$OUT"; }
have(){ command -v "$1" >/dev/null 2>&1; }

JQ=jq; have jq || JQ=cat
compose() { docker compose -p "$PROJ" $(printf " -f %q" "${STACK_FILES[@]}") "$@"; }
curlj() { curl -sfS --max-time 8 -H "Accept: application/json" "$@" || return $?; }
record_json () { local k="$1"; shift; printf '{ "%s": %s }\n' "$k" "$*" >> "$JSON"; }

echo "{}" > "$JSON"

sep "1) Compose config validation"
if compose config --quiet; then ok "Compose config OK"; else err "Compose config invalid"; exit 1; fi

sep "2) Containers & ports"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee -a "$OUT"

sep "3) Network alignment (expect ${PROJ}_appnet)"
docker ps --format "table {{.Names}}\t{{.Networks}}" | tee -a "$OUT"

HOST_OBSERVER="http://localhost:8070"
HOST_RCA="http://localhost:8082"
HOST_HARDEN="http://localhost:8083"
HOST_ATTACK="http://localhost:8084"
HOST_PROM="http://localhost:9090"
HOST_AM="http://localhost:9093"
HOST_GRAFANA="http://localhost:3001"

sep "4) Health endpoints"
declare -a NAMES=(observer_hub rca_ai hardening_ai attack_driver)
declare -a URLS=("$HOST_OBSERVER/health" "$HOST_RCA/health" "$HOST_HARDEN/health" "$HOST_ATTACK/health")
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"; url="${URLS[$i]}"
  if out=$(curlj "$url"); then ok "$name /health: $(echo "$out"|$JQ .)"; record_json "${name}_health" "$out"; else err "$name /health FAILED"; fi
done

sep "5) Observer /status + /risks"
if out=$(curlj "$HOST_OBSERVER/status"); then ok "/status: $(echo "$out" | $JQ .)"; record_json observer_status "$out"; else err "/status FAILED"; fi
if out=$(curlj "$HOST_OBSERVER/risks");  then ok "/risks: $(echo "$out" | $JQ .)";   record_json observer_risks  "$out"; else err "/risks FAILED"; fi

sep "6) DNS/Env from observer_hub"
if compose ps -q observer_hub >/dev/null 2>&1; then
  # Print relevant env seen inside the container
  compose exec -T observer_hub /bin/sh -lc 'echo "ENV:"; echo PROM_URL=$PROM_URL; echo ALERT_URL=$ALERT_URL' | tee -a "$OUT" || true
  # Try resolving names
  if out=$(compose exec -T observer_hub python - <<'PY'
import socket, json, os, sys
r={}
for n in ("prometheus","alertmanager"):
  try: r[n]=socket.gethostbyname(n)
  except Exception as e: r[n]=f"ERR:{e}"
r["ALERT_URL"]=os.environ.get("ALERT_URL","")
print(json.dumps(r))
PY
  ); then
    echo "$out" | $JQ . | tee -a "$OUT"; record_json dns_from_observer "$out"
  else err "exec into observer_hub failed"; fi
fi

sep "7) Prometheus API"
if out=$(curlj "$HOST_PROM/api/v1/status/runtimeinfo"); then ok "Prom status OK"; record_json prom_runtimeinfo "$out"; else err "Prometheus not reachable"; fi
if out=$(curlj --get "$HOST_PROM/api/v1/query" --data-urlencode 'query=up'); then ok "Prom query(up) OK"; record_json prom_query_up "$out"; else err "Prom query(up) FAILED"; fi

sep "8) Alertmanager API"
if out=$(curlj "$HOST_AM/api/v2/status"); then ok "Alertmanager status OK"; record_json am_status "$out"; else err "Alertmanager not reachable"; fi
if out=$(curlj "$HOST_AM/api/v2/alerts"); then ok "Alert list OK"; record_json am_alerts "$out"; else err "Alert list FAILED"; fi

sep "9) Grafana health"
if out=$(curlj "$HOST_GRAFANA/api/health"); then ok "Grafana health: $(echo "$out"|$JQ .)"; record_json grafana_health "$out"; else err "Grafana not reachable"; fi

sep "10) metrics_tuner output"
ls -l infra/prometheus/rules 2>/dev/null | tee -a "$OUT" || warn "rules dir missing"
test -s infra/prometheus/rules/_generated.yml && ok "_generated.yml present" || warn "no _generated.yml yet"

sep "11) RCA + Attack"
if out=$(curlj -X POST "$HOST_RCA/diagnose"); then ok "RCA diagnose OK"; record_json rca_diagnose "$out"; else err "RCA diagnose FAILED"; fi
if out=$(curlj -X POST "$HOST_ATTACK/run" -H 'Content-Type: application/json' -d '{"mode":"recon"}'); then ok "Attack driver OK"; record_json attack_run "$out"; else err "Attack driver /run FAILED"; fi

sep "12) Final summary"
echo "Report: $OUT" | tee -a "$OUT"
echo "JSON  : $JSON" | tee -a "$OUT"
echo "Done."
