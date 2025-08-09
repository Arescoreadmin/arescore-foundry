#!/usr/bin/env bash
set -euo pipefail

say(){ printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }
write(){ mkdir -p "$(dirname "$1")"; printf "%s" "$2" > "$1"; say "Wrote $1"; }

PY_BASE="python:3.11-slim"          # pinned family
NODE_BASE="node:18-alpine"          # pinned family
NGINX_BASE="nginxinc/nginx-unprivileged:stable-alpine"

# ---------- Orchestrator (FastAPI/uvicorn) ----------
ORCH=$(cat <<'DOCKER'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# non-root user
RUN useradd -u 10001 -m appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD python - <<'PY' || exit 1
import urllib.request as u
u.urlopen("http://127.0.0.1:8000/ready", timeout=2).read(); print("ok")
PY

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
DOCKER
)

# ---------- Log Indexer (FastAPI) ----------
INDEXER=$(cat <<'DOCKER'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# non-root user
RUN useradd -u 10001 -m appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

COPY indexer.py .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD python - <<'PY' || exit 1
import urllib.request as u
u.urlopen("http://127.0.0.1:8080/health", timeout=2).read(); print("ok")
PY

CMD ["python","indexer.py"]
DOCKER
)

# ---------- Frontend (Vite build → Nginx runtime) ----------
FRONTEND=$(cat <<'DOCKER'
# Build
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

# Runtime (already non-root in this image)
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ready || exit 1
DOCKER
)

# ---------- Write canonical Dockerfiles ----------
write orchestrator/Dockerfile     "$ORCH"
write log_indexer/Dockerfile      "$INDEXER"
write frontend/Dockerfile         "$FRONTEND"

# ---------- Write duplicate paths (to resolve PR conflicts now) ----------
write infra/orchestrator/Dockerfile   "$ORCH"
write infra/log_indexer/Dockerfile    "$INDEXER"
write infra/frontend/Dockerfile       "$FRONTEND"

# Backend duplicates (temporary; will be removed in consolidation PR)
for svc in behavior_analytics log_indexer mutation_engine orchestrator sentinelcore sentinelred; do
  case "$svc" in
    orchestrator)      body="$ORCH" ;;
    log_indexer)       body="$INDEXER" ;;
    *)                 body="$ORCH" ;;   # Python template as safe default
  esac
  write "backend/${svc}/Dockerfile" "$body"
done

say "All Dockerfiles reconciled with pinned bases and non-root users."
say "Next:"
echo "  git add -A && git commit -m 'Resolve Dockerfile conflicts: pinned base + non-root + healthchecks' && git push"
