# create docs/MVP-RUNBOOK.md
mkdir -p docs
cat > docs/MVP-RUNBOOK.md <<'MD'
# MVP Runbook

**Scope:** Start the app (frontend + orchestrator), verify health, hardening, gzip, and metrics.  
**Out of scope (post-MVP):** Full Grafana/Alertmanager (optional section below).

## Prereqs
- Docker & Docker Compose v2
- Repo paths match:
  - `infra/docker-compose.yml`
  - `infra/docker-compose.hardening.override.yml`
  - `infra/docker-compose.frontend-tmpfs.override.yml`
  - Scripts in `scripts/`

## 1) Boot the stack
Minimal (works for MVP):
```sh
docker compose -f infra/docker-compose.yml up -d --build
