#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
DF_PATH="services/orchestrator/Dockerfile"
EP_PATH="services/orchestrator/entrypoint.sh"
REQ_PATH="services/orchestrator/app/requirements.txt"
ENV_ARG=()
[ -n "${ENV_FILE:-}" ] && ENV_ARG=(--env-file "$ENV_FILE")

echo "==> Hardening orchestrator image & entrypoint"
echo "Repo: $ROOT"

mkdir -p "$(dirname "$REQ_PATH")"
touch "$REQ_PATH"
grep -Eq '^[[:space:]]*fastapi([=<>]|$)' "$REQ_PATH" || echo 'fastapi==0.115.*' >> "$REQ_PATH"
grep -Eq '^[[:space:]]*uvicorn([=<>]|$)' "$REQ_PATH" || echo 'uvicorn==0.30.*' >> "$REQ_PATH"

mkdir -p "$(dirname "$EP_PATH")"
cat > "$EP_PATH" <<'ENTRY'
#!/usr/bin/env sh
set -eu
python - <<'PY' || exit 90
import importlib
m = importlib.import_module("app.main")
assert hasattr(m, "app"), "Expected 'app' in app.main (FastAPI instance)"
PY
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
ENTRY
chmod +x "$EP_PATH"

mkdir -p "$(dirname "$DF_PATH")"
cat > "$DF_PATH" <<'DOCKER'
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/_generated /app/services/_generated
COPY services/orchestrator/app /app/app
COPY services/orchestrator/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c 'import urllib.request,sys; sys.exit(0 if urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2).getcode()==200 else 1)'
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
DOCKER

echo "==> Validating compose"
docker compose "${ENV_ARG[@]}" -f compose.yml -f compose.federated.yml config >/dev/null

echo "==> Rebuilding orchestrator"
docker compose "${ENV_ARG[@]}" -f compose.yml -f compose.federated.yml build --no-cache orchestrator

echo "==> Starting orchestrator"
docker compose "${ENV_ARG[@]}" -f compose.yml -f compose.federated.yml up -d orchestrator

echo "==> Probing /health (host)"
curl -fsS http://127.0.0.1:8080/health && echo "OK: host probe"

echo "==> Probing /health (sidecar)"
ORCH_CID="$(docker compose "${ENV_ARG[@]}" ps -q orchestrator)"
[ -n "$ORCH_CID" ] && docker run --rm --network "container:${ORCH_CID}" curlimages/curl:8.10.1 -fsS http://127.0.0.1:8080/health && echo "OK: sidecar probe" || echo "WARN: no container id"
