#!/bin/bash

set -e

echo "🔧 Patching Python backend services with Prometheus instrumentation..."

# Define services and their entrypoints
declare -A services=(
  ["orchestrator"]="app/main.py"
  ["observer_hub"]="app.py"
  ["rca_ai"]="app.py"
  ["hardening_ai"]="app.py"
  ["attack_driver"]="driver.py"
  ["metrics_tuner"]="cron.py"
  ["log_indexer"]="indexer.py"
)

# Prometheus FastAPI instrumentation snippet
read -r -d '' METRICS_SNIPPET <<'EOF'
from prometheus_fastapi_instrumentator import Instrumentator

try:
    Instrumentator().instrument(app).expose(app)
except Exception as e:
    print(f"⚠️ Failed to patch Prometheus metrics: {e}")
EOF

# Iterate through each service and patch if not already instrumented
for service in "${!services[@]}"; do
  file="backend/${service}/${services[$service]}"
  if [[ -f "$file" ]]; then
    if grep -q 'prometheus_fastapi_instrumentator' "$file"; then
      echo "✅ $service already instrumented."
    else
      echo "⚙️  Instrumenting $service..."
      echo -e "\n$METRICS_SNIPPET" >> "$file"
      echo "📎 $file patched."
    fi
  else
    echo "⛔️ File not found: $file (skipped)"
  fi
done

echo "✅ All services patched with Prometheus instrumentation where applicable."
