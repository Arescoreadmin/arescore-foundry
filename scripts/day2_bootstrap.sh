#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"
echo "==> Day 2 setup at $ROOT"

# 0) Preconditions
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
command -v docker compose >/dev/null || { echo "docker compose v2 required"; exit 1; }

# 1) Scaffolding (explicit, no brace magic)
mkdir -p services/fl_coordinator/app
mkdir -p services/consent_registry/app
mkdir -p services/evidence_bundler/app
mkdir -p scripts

# 2) Minimal FastAPI apps
cat > services/fl_coordinator/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ
cat > services/fl_coordinator/app/main.py <<'PY'
from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
@app.get("/ping")
def ping(): return {"pong": True}
PY

cat > services/consent_registry/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ
cat > services/consent_registry/app/main.py <<'PY'
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
class OptIn(BaseModel):
    subject_id: str | None = None
    model_hash: str | None = None
@app.post("/consent/training/optin")
def optin(payload: OptIn | None = None):
    return {"status":"opted_in","subject": (payload.subject_id if payload else None)}
@app.get("/crl")
def crl(): return {"serials": []}
PY

cat > services/evidence_bundler/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ
cat > services/evidence_bundler/app/main.py <<'PY'
from fastapi import FastAPI
from pydantic import BaseModel
import uuid
app = FastAPI()
@app.get("/health")
def health(): return {"ok": True}
class Evidence(BaseModel):
    run_id: str | None = None
    notes: str | None = None
@app.post("/evidence")
def add_evidence(ev: Evidence):
    return {"evidence_id": str(uuid.uuid4()), "received": ev.model_dump()}
PY

# 3) Dockerfiles
for svc in fl_coordinator consent_registry evidence_bundler; do
  cat > "services/${svc}/Dockerfile" <<DOCKER
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY services/_generated /app/services/_generated
COPY services/${svc}/app /app/app
RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi
ENV PYTHONPATH=/app
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2); print('ok')" || exit 1
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
DOCKER
done

# 4) Compose overlay
cat > compose.federated.yml <<'YAML'
services:
  fl_coordinator:
    build:
      context: .
      dockerfile: services/fl_coordinator/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9092:8080"
    restart: unless-stopped

  consent_registry:
    build:
      context: .
      dockerfile: services/consent_registry/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9093:8080"
    restart: unless-stopped

  evidence_bundler:
    build:
      context: .
      dockerfile: services/evidence_bundler/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9094:8080"
    restart: unless-stopped#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"
echo "==> Day 2 setup at $ROOT"

# 0) Preconditions
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
command -v docker compose >/dev/null || { echo "docker compose v2 required"; exit 1; }

# 1) Scaffolding for three services
mkdir -p services/{fl_coordinator,consent_registry,evidence_bundler}/{app}
mkdir -p scripts

# 2) Minimal FastAPI apps

cat > services/fl_coordinator/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ

cat > services/fl_coordinator/app/main.py <<'PY'
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/ping")
def ping(): return {"pong": True}
PY

cat > services/consent_registry/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ

cat > services/consent_registry/app/main.py <<'PY'
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/health")
def health(): return {"ok": True}

class OptIn(BaseModel):
    subject_id: str | None = None
    model_hash: str | None = None

@app.post("/consent/training/optin")
def optin(payload: OptIn | None = None):
    return {"status":"opted_in","subject": (payload.subject_id if payload else None)}

# simple CRL shim so /crl responds (empty list for now)
@app.get("/crl")
def crl(): return {"serials": []}
PY

cat > services/evidence_bundler/app/requirements.txt <<'REQ'
fastapi==0.115.*
uvicorn==0.30.*
REQ

cat > services/evidence_bundler/app/main.py <<'PY'
from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI()

@app.get("/health")
def health(): return {"ok": True}

class Evidence(BaseModel):
    run_id: str | None = None
    notes: str | None = None

@app.post("/evidence")
def add_evidence(ev: Evidence):
    return {"evidence_id": str(uuid.uuid4()), "received": ev.model_dump()}
PY

# 3) Dockerfiles (reuse the orchestrator pattern, healthcheck via Python)
for svc in fl_coordinator consent_registry evidence_bundler; do
  cat > "services/${svc}/Dockerfile" <<'DOCKER'
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY services/_generated /app/services/_generated
COPY services/___SVC___/app /app/app

RUN python -m pip install --upgrade pip && \
    if [ -f /app/app/requirements.txt ]; then pip install -r /app/app/requirements.txt; fi

ENV PYTHONPATH=/app
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/health', timeout=2); print('ok')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
DOCKER
  # replace placeholder path
  sed -i "s#___SVC___#${svc}#g" "services/${svc}/Dockerfile"
done

# 4) Compose overlay (adds the three services)
cat > compose.federated.yml <<'YAML'
services:
  fl_coordinator:
    build:
      context: .
      dockerfile: services/fl_coordinator/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9092:8080"
    restart: unless-stopped

  consent_registry:
    build:
      context: .
    dockerfile: services/consent_registry/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9093:8080"
    restart: unless-stopped

  evidence_bundler:
    build:
      context: .
      dockerfile: services/evidence_bundler/Dockerfile
    depends_on:
      orchestrator:
        condition: service_started
    ports:
      - "9094:8080"
    restart: unless-stopped
YAML

# fix YAML indentation typo in consent_registry (compose is picky)
awk '1' compose.federated.yml | sed 's/^    dockerfile:/      dockerfile:/' > /tmp/compose.fed.yml && mv /tmp/compose.fed.yml compose.federated.yml

# 5) Seed script (placeholder you can extend later)
cat > scripts/seed_model_registry.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "==> Seeding model registry (placeholder)"
# If you later expose a POST /models endpoint on orchestrator or a registry service,
# add curl commands here to register allowed model hashes, etc.
exit 0
SH
chmod +x scripts/seed_model_registry.sh

# 6) Build + boot with overlay (staging layer kept in case you already use it)
# If compose.staging.yml doesn't exist, we skip it.
FILES=(-f compose.yml)
[ -f compose.staging.yml ] && FILES+=(-f compose.staging.yml)
FILES+=(-f compose.federated.yml)

echo "==> Building & starting with overlay: ${FILES[*]}"
docker compose "${FILES[@]}" up -d --build

# 7) Smokes
echo "==> Seed"
./scripts/seed_model_registry.sh

echo "==> Smoke: consent opt-in"
curl -sX POST http://localhost:9093/consent/training/optin | tr -d '\n'; echo

echo "==> Smoke: CRL (empty)"
curl -s http://localhost:9093/crl | tr -d '\n'; echo

echo "==> Health: fl_coordinator"
curl -s http://localhost:9092/health | tr -d '\n'; echo

echo "==> Health: evidence_bundler"
curl -s http://localhost:9094/health | tr -d '\n'; echo

echo "==> Day 2 overlay up and responding."

YAML

# 5) Seed script (placeholder)
cat > scripts/seed_model_registry.sh <<'SEED'
#!/usr/bin/env bash
set -euo pipefail
echo "==> Seeding model registry (placeholder)"
exit 0
SEED
chmod +x scripts/seed_model_registry.sh

# 6) Build + boot with overlay (+ staging if present)
FILES=(-f compose.yml)
[ -f compose.staging.yml ] && FILES+=(-f compose.staging.yml)
FILES+=(-f compose.federated.yml)
echo "==> Building & starting: ${FILES[*]}"
docker compose "${FILES[@]}" up -d --build

# 7) Smokes
echo "==> Seed"
./scripts/seed_model_registry.sh
echo "==> Smoke: consent opt-in"
curl -sX POST http://localhost:9093/consent/training/optin | tr -d '\n'; echo
echo "==> Smoke: CRL (empty)"
curl -s http://localhost:9093/crl | tr -d '\n'; echo
echo "==> Health: fl_coordinator"
curl -s http://localhost:9092/health | tr -d '\n'; echo
echo "==> Health: evidence_bundler"
curl -s http://localhost:9094/health | tr -d '\n'; echo
echo "==> Day 2 overlay up and responding."
