#!/usr/bin/env bash
set -euo pipefail

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
write(){ mkdir -p "$(dirname "$1")"; printf "%s" "$2" > "$1"; say "Wrote $1"; }

# ---------- TEMPLATES (proven locally) ----------

ORCH_DOCKER='
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD ["python","-c","import urllib.request as u; u.urlopen(\"http://127.0.0.1:8000/ready\", timeout=2).read(); print(\"ok\")"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
'

INDEXER_DOCKER='
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
COPY indexer.py .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD ["python","-c","import urllib.request as u; u.urlopen(\"http://127.0.0.1:8080/health\", timeout=2).read(); print(\"ok\")"]
CMD ["python","indexer.py"]
'

# Generic FastAPI python service (until their real apps land)
GEN_PY_DOCKER='
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd -u 10001 -m appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt
# Expect code under app/
COPY app ./app
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD ["python","-c","import urllib.request as u; u.urlopen(\"http://127.0.0.1:8000/ready\", timeout=2).read(); print(\"ok\")"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
'

FRONTEND_DOCKER='
# Build
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build
# Runtime (non-root)
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ready || exit 1
'

NGINX_CONF='
server {
  listen 8080;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  location / { try_files $uri /index.html; }

  # Simple readiness
  location = /ready {
    default_type application/json;
    return 200 "{\"ready\":true}";
  }

  # Proxy API to orchestrator
  location /api/ {
    proxy_pass http://orchestrator:8000/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Connection "";
    proxy_redirect off;
  }
}
'

# ---------- WRITE RESOLUTIONS (all paths GitHub shows in conflicts) ----------
say "Resolving Dockerfile conflicts with pinned base + non-root + healthchecks"

# Canonical services
write orchestrator/Dockerfile        "$ORCH_DOCKER"
write log_indexer/Dockerfile         "$INDEXER_DOCKER"
write frontend/Dockerfile            "$FRONTEND_DOCKER"
write frontend/nginx.conf            "$NGINX_CONF"

# infra duplicates (present in the PR conflict list)
write infra/orchestrator/Dockerfile  "$ORCH_DOCKER"
write infra/log_indexer/Dockerfile   "$INDEXER_DOCKER"
write infra/frontend/Dockerfile      "$FRONTEND_DOCKER"

# backend duplicates (present in the conflict list)
write backend/orchestrator/Dockerfile        "$ORCH_DOCKER"
write backend/log_indexer/Dockerfile         "$INDEXER_DOCKER"
for svc in behavior_analytics mutation_engine sentinelcore sentinelred; do
  write "backend/${svc}/Dockerfile" "$GEN_PY_DOCKER"
done

say "Done. Review changes, then commit and push this PR branch."
