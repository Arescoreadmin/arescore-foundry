#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

echo "==> Repo root: $ROOT"

# 0) Preconditions that keep you from crying later
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
command -v docker compose >/dev/null || { echo "docker compose v2 required"; exit 1; }

mkdir -p services/orchestrator/app services/spawn_service/app services/_generated policies scripts

# 1) Pin OPA digest (pull once, grab actual digest)
echo "==> Pinning OPA digest"
docker pull openpolicyagent/opa:1.10.0 >/dev/null
OPA_DIGEST="$(docker image inspect --format='{{index .RepoDigests 0}}' openpolicyagent/opa:1.10.0)"
echo "    OPA_DIGEST=$OPA_DIGEST"

# 2) Ensure Python package markers and generated stubs exist
touch services/__init__.py services/_generated/__init__.py \
      services/orchestrator/__init__.py services/orchestrator/app/__init__.py \
      services/spawn_service/__init__.py services/spawn_service/app/__init__.py

# 3) Write production-ready Dockerfiles + entrypoint for orchestrator
echo "==> Writing Dockerfiles"
cat > services/orchestrator/Dockerfile <<'DOCKER'
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Bring in generated stubs and app code
COPY services/_generated /app/services/_generated
COPY services/orchestrator/app /app/app
COPY services/orchestrator/entrypoint.sh /entrypoint.sh

# Optional deps if present inside app/
RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi && \
    chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
EXPOSE 8080

# Healthcheck without curl
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2); print('ok')" || exit 1

CMD ["/entrypoint.sh"]
DOCKER

cat > services/orchestrator/entrypoint.sh <<'ENTRY'
#!/usr/bin/env sh
set -eu

# Try ASGI via uvicorn if app.main:app exists, else fallback to python -m app.main
if python - <<'PY'
try:
    import importlib
    m = importlib.import_module("app.main")
    assert hasattr(m, "app")
except Exception:
    raise SystemExit(1)
PY
then
  # Use uvicorn if available, otherwise install it quickly
  if ! python -c "import uvicorn" 2>/dev/null; then
    pip install --no-cache-dir uvicorn >/dev/null 2>&1 || true
  fi
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
else
  exec python -m app.main
fi
ENTRY

cat > services/spawn_service/Dockerfile <<'DOCKER'
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/_generated /app/services/_generated
COPY services/spawn_service/app /app/app

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi

ENV PYTHONPATH=/app
CMD ["python", "-m", "app.main"]
DOCKER

# 4) Clean Compose v2 file
echo "==> Writing compose.yml"
cp -f compose.yml "compose.yml.bak.$(date +%s)" 2>/dev/null || true
cat > compose.yml <<YAML
services:
  opa:
    image: ${OPA_DIGEST}
    command: ["run", "--server", "/policies"]
    volumes:
      - ./policies:/policies:ro
    read_only: true
    healthcheck:
      test: ["CMD", "opa", "eval", "1==1"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  orchestrator:
    build:
      context: .
      dockerfile: services/orchestrator/Dockerfile
    depends_on:
      opa:
        condition: service_started
    ports:
      - "8080:8080"
    restart: unless-stopped

  spawn_service:
    build:
      context: .
    dockerfile: services/spawn_service/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    restart: unless-stopped
YAML

# 5) Ensure .dockerignore so you don’t ship your whole life into the image
echo "==> Writing .dockerignore"
cat > .dockerignore <<'IGN'
.git
.venv
__pycache__/
*.pyc
policies/_misc/
IGN

# 6) Guardrail: run OPA tests before building
echo "==> Validating OPA policies (opa:1.10.0)"
docker run --rm -v "$PWD/policies":/policies:ro openpolicyagent/opa:1.10.0 test /policies -v

# 7) Build images and start stack
echo "==> Building images"
docker compose build --no-cache

echo "==> Starting stack"
docker compose up -d --force-recreate

# 8) Health probes
echo "==> Probing OPA"
OPA_CID="$(docker ps --filter name=opa --format '{{.ID}}' | head -n1)"
test -n "$OPA_CID"
docker exec "$OPA_CID" opa eval '1==1' >/dev/null

echo "==> Probing orchestrator /health from sidecar curl"
ORCH_CID="$(docker ps --filter name=orchestrator --format '{{.ID}}' | head -n1)"
test -n "$ORCH_CID"
docker run --rm --network "container:${ORCH_CID}" curlimages/curl:8.10.1 -fsS http://127.0.0.1:8080/health >/dev/null

echo "==> All good. OPA healthy, orchestrator healthy."
