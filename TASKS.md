# TASKS — Sentinel Forge

## Conventions
- Each task must open a PR titled `[forge-###] <title>`.
- Each PR must include: ✅ Acceptance proof, 🛡 Security notes, 📜 Changelog snippet.
- Run locally with `docker compose up --build` unless CI is required.

---

- id: forge-001
  title: Recreate Dockerfiles + Compose (secure)
  plan:
    - Add Dockerfiles for all Python/Node services:
      - Base: `python:3.11-slim` / `node:20-alpine`
      - Non-root user, `--no-cache` installs, pinned deps
      - Multi-stage builds, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
      - `HEALTHCHECK` calling `/ready`
    - Create `infra/docker-compose.yml` wiring ports, networks, healthchecks
    - Add `.dockerignore` for each service
  deliverables:
    - `*/Dockerfile`, `.dockerignore`, `infra/docker-compose.yml`
  acceptance:
    - `docker compose build` passes
    - `curl localhost:8000/health` → 200 for orchestrator
    - All containers report `healthy` within 60s

- id: forge-002
  title: Structured JSON logging + redaction + LogIndexer hash chain
  plan:
    - Add logging middleware to every FastAPI service
    - Implement redaction by key match list from `REDACT_KEYS`
    - Build `log_indexer/` (Fluent Bit config + Python hash chain sidecar)
  deliverables:
    - `common/logging.py`, `log_indexer/*`
  acceptance:
    - Logs contain `svc,lvl,evt,trace` and redact secrets
    - Chain hash visible in indexer stdout and rotates every N entries

- id: forge-003
  title: Health/Readiness + Self-Healing Supervisor
  plan:
    - Implement `/health` and `/ready` across services
    - `self_healing_supervisor/` that watches Docker health and restarts unhealthy
  deliverables:
    - `*/main.py` endpoints; `self_healing_supervisor/*`
  acceptance:
    - Killing a service triggers supervisor restart within 10s (local demo)

- id: forge-004
  title: Security Hardening Pass 1
  plan:
    - Drop root, read-only FS, `CAP_DROP=ALL`, `no-new-privileges`
    - Network egress allowlist via Compose
    - Add rate limiting middleware + JWT validation helpers
  deliverables:
    - Updated Dockerfiles/compose; `common/security.py`
  acceptance:
    - Containers run as non-root; `whoami` → `svcuser`
    - Requests without valid JWT return 401

- id: forge-005
  title: CI pipeline + gates
  plan:
    - GitHub Actions: lint, typecheck, tests, docker build, Trivy scan, SBOM
    - Require PR checks in repo rules
  deliverables:
    - `.github/workflows/ci.yml`, `trivyignore`, `CODEOWNERS`
  acceptance:
    - CI passes on sample PR; failed Trivy blocks merge

- id: forge-006
  title: Golden Path E2E test
  plan:
    - Add `tests/e2e/test_defense_flow.py`
    - Start compose, post synthetic event → mitigation → log → optional quarantine → notify
  deliverables:
    - E2E test + sample fixture
  acceptance:
    - Test green locally and in CI (spin minimal stack)

- id: forge-007
  title: Notification Dispatcher (email/webhook) MVP
  plan:
    - Provide `/notify` endpoint (email via SMTP mock, webhook to httpbin)
  deliverables:
    - `notification_dispatcher/*`
  acceptance:
    - E2E triggers one email log + one webhook 200

- id: forge-008
  title: SentinelCore defend endpoint MVP
  plan:
    - `POST /defend` accepts JSON telemetry, returns mitigation
    - Scoring = deterministic heuristic (placeholder), include `X-Trace-Id`
  deliverables:
    - `sentinelcore/main.py`, tests
  acceptance:
    - Unit tests cover high/low score branches; returns 200 with plan

- id: forge-009
  title: SentinelRed toggle + guardrails
  plan:
    - Feature flag `ENABLE_SENTINELRED` (off by default)
    - Require signed admin token to run any active probe
  deliverables:
    - `sentinelred/*`, flag wiring in compose
  acceptance:
    - With flag off endpoints return 403; with flag on + admin token → 200

- id: forge-010
  title: Docs + PR template
  plan:
    - Add `SECURITY.md`, `CONTRIBUTING.md`, PR template with checklists
  deliverables:
    - `SECURITY.md`, `.github/PULL_REQUEST_TEMPLATE.md`
  acceptance:
    - Template loads on PR; docs reflect current stack
