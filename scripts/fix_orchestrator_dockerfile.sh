#!/usr/bin/env bash
set -euo pipefail
cat > services/orchestrator/Dockerfile <<'DOCKER'
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
docker compose -f compose.yml -f compose.federated.yml build orchestrator --no-cache
docker compose -f compose.yml -f compose.federated.yml up -d orchestrator
