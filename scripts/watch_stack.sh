#!/bin/bash

while true; do
  clear
  echo "🛰  ARESCORE FOUNDRY STACK STATUS – $(date '+%Y-%m-%d %H:%M:%S')"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  echo -e "\n📦 Docker Containers:"
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

  echo -e "\n📊 Prometheus Targets (UP status):"
  curl -s localhost:9090/api/v1/query?query=up | jq '.data.result[] | "\(.metric.job) => \(.value[1])"' | sed 's/"//g'

  echo -e "\n🚨 Alerts Fired:"
  curl -s localhost:9090/api/v1/alerts | jq -r '.data.alerts[]? | select(.state=="firing") | "\(.labels.alertname) - \(.annotations.description)"' || echo "✅ No alerts firing."

  echo -e "\n❤️ FastAPI Health Checks:"
  for svc in orchestrator observer_hub metrics_tuner rca_ai; do
    url="http://localhost:$(docker inspect -f '{{range $p, $conf := .NetworkSettings.Ports}}{{if eq $p "8000/tcp"}}{{(index $conf 0).HostPort}}{{end}}{{end}}' $svc 2>/dev/null)"
    [ -z "$url" ] && continue
    echo -n "$svc: "
    curl -s "$url/health" || echo "❌ Unavailable"
  done

  echo -e "\n🧾 Orchestrator Logs (tail -5):"
  docker logs orchestrator --tail 5 2>/dev/null || echo "❌"

  echo -e "\n📐 Metrics Tuner Logs (tail -5):"
  docker logs metrics_tuner --tail 5 2>/dev/null || echo "❌"

  echo -e "\n🔁 Refreshing in 5 seconds... (CTRL+C to quit)"
  sleep 5
done
