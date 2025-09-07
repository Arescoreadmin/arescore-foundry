#!/usr/bin/env bash
set -euo pipefail

# REPO should be "owner/name" (defaults to current if omitted)
REPO="${REPO:-}"

# --- Ensure gh is logged in ---
if ! gh auth status &>/dev/null; then
  echo "Please run: gh auth login"
  exit 1
fi

# --- Create labels (idempotent) ---
mklabel() {
  local name="$1" color="$2" desc="$3"
  gh label create "$name" --color "$color" --description "$desc" ${REPO:+--repo "$REPO"} 2>/dev/null || \
  gh label edit "$name" --color "$color" --description "$desc" ${REPO:+--repo "$REPO"} >/dev/null
}

mklabel "priority/P0" "d73a4a" "Critical path / blocks release"
mklabel "priority/P1" "fbca04" "High priority / next up"
mklabel "priority/P2" "0e8a16" "Medium priority"
mklabel "type/infra" "0052CC" "Infra / Docker / Compose / Nginx"
mklabel "type/ci" "5319e7" "CI/CD / supply-chain"
mklabel "type/security" "b60205" "Security / secrets / hardening"
mklabel "type/runtime" "1d76db" "Runtime code / endpoints / logging"
mklabel "area/frontend" "0e8a16" "Frontend / Vite / Nginx"
mklabel "area/orchestrator" "5319e7" "Orchestrator service"
mklabel "area/log_indexer" "fbca04" "Log indexer service"
mklabel "status/blocked" "000000" "Blocked on external dependency"
mklabel "good-first-task" "7057ff" "Small, contained task"

# --- Helper to open an issue from here-doc ---
open_issue() {
  local title="$1"; local labels="$2"
  shift 2
  local body
  body="$(cat)"
  gh issue create ${REPO:+--repo "$REPO"} --title "$title" --label "$labels" --body "$body"
}

# --------------------------- P0: FIX BROKEN STUFF ---------------------------

open_issue "Consolidate service directories & fix compose contexts" \
"type/infra,priority/P0,area/orchestrator,area/log_indexer,area/frontend" <<'MD'
## Why
Duplicate trees (`backend/*`) risk drift. Single-source per service simplifies builds and reviews.

## Scope
- Remove `/backend/*` duplicates; keep `/orchestrator`, `/log_indexer`, `/frontend`, `/infra`.
- Update `infra/docker-compose.yml` build contexts to `../<service>`.
- Ensure images build and run.

## Acceptance Criteria
- `docker compose up -d` → all services **healthy** in <60s.
- `curl http://localhost:3000/api/ready` → 200 JSON.
- No references to removed `backend/*`.
- Screenshots/logs of `docker compose ps`.

## Branch
feat/structure-consolidate
MD

open_issue "Finalize /api proxy via Nginx (no CORS) + runtime config" \
"type/infra,priority/P0,area/frontend" <<'MD'
## Why
Keep single-origin dev/prod, avoid CORS.

## Scope
- `frontend/nginx.conf`: `location /api/ { proxy_pass http://orchestrator:8000/; ... }`
- `frontend/public/config.js`: `API_BASE = '/api'`.
- Rebuild frontend image.

## Acceptance Criteria
- `nginx -t` passes in container.
- `curl http://localhost:3000/api/ready` returns orchestrator JSON (not HTML).
- Commit includes config + Nginx.

## Branch
feat/proxy-stable
MD

open_issue "Add /ready to all services + compose healthchecks + restart policies" \
"type/runtime,priority/P0,area/orchestrator,area/log_indexer,area/frontend" <<'MD'
## Why
Uniform readiness + auto-recovery; avoid startup coupling.

## Scope
- Add `@app.get('/ready')` to services (frontend served by Nginx—already 200 on `/`).
- Compose: `healthcheck` hits `/ready`; `restart: unless-stopped`.
- Remove unnecessary `depends_on`.

## Acceptance Criteria
- Kill/restart any single container → recovers to **healthy**.
- `docker compose ps` shows **healthy**.
- Short note on what readiness checks (basic for now).

## Branch
feat/health-ready-everywhere
MD

open_issue "Orchestrator healthcheck support (curl or Python)" \
"type/infra,priority/P0,area/orchestrator" <<'MD'
## Why
Existing HEALTHCHECK used curl which wasn’t installed.

## Scope
- Either install `curl` in `orchestrator/Dockerfile` or switch HEALTHCHECK to Python.
- Keep pinned base and non-root.

## Acceptance Criteria
- Orchestrator becomes **healthy** within 40s of start.
- Dockerfile shows pinned base and non-root user.

## Branch
chore/orchestrator-healthcheck-tools
MD

open_issue "Run as non-root + pinned base images across services" \
"type/security,priority/P0,area/orchestrator,area/log_indexer,area/frontend" <<'MD'
## Why
Hardening and predictable builds.

## Scope
- `python:3.11-slim`, `node:18-alpine`, `nginx-unprivileged:stable-alpine`.
- Add non-root users (`USER appuser`), fix ownership.
- Keep HEALTHCHECKs.

## Acceptance Criteria
- `docker compose run --rm orchestrator id -u` ≠ 0 (same for others).
- Images build clean; services start healthy.

## Branch
sec/nonroot-pins
MD

open_issue "Structured logging emitter to log_indexer (non-blocking)" \
"type/runtime,priority/P0,area/orchestrator,area/log_indexer" <<'MD'
## Why
We defined LOG_* envs but don’t emit logs.

## Scope
- Add `log.py` helper (async `httpx` + timeout/backoff).
- Emit `startup`, `request` events with `{ts, svc, evt, request_id?}`.
- Best-effort: failures don’t block.

## Acceptance Criteria
- Logs appear in log_indexer with hash chain.
- When indexer is down, API still responds; when back up, logs resume.

## Branch
feat/logging-emitter
MD

open_issue "Remove plaintext defaults; support *_FILE secrets" \
"type/security,priority/P0,area/orchestrator,area/log_indexer" <<'MD'
## Why
Get rid of `changeme-*` in code; prepare for Docker secrets.

## Scope
- No default secrets in code; env or `*_FILE` only.
- Add `.env.example` (placeholders only).
- Compose accepts `secrets:` in a follow-up.

## Acceptance Criteria
- `git grep -n 'changeme'` → 0 hits.
- Services run with envs; doc updated.

## Branch
sec/secrets-envfile-stage1
MD

# --------------------------- P1+: UPGRADES ---------------------------

open_issue "CI supply-chain gates: SBOM + Trivy + Dockerfile lint" \
"type/ci,priority/P1" <<'MD'
## Why
Block regressions & vulnerable images.

## Scope
- GitHub Actions: buildx, Syft SBOM, Trivy scan (fail on HIGH/CRITICAL), Hadolint.
- Upload SBOM artifact; status checks required on PRs.
- Optionally push to GHCR on main.

## Acceptance Criteria
- PRs blocked when scan fails.
- SBOM published as artifact.
- Example run links in PR.

## Branch
ci/supply-chain
MD

open_issue "Observability v1: X-Request-ID + basic /metrics placeholders" \
"type/runtime,priority/P1" <<'MD'
## Why
Traceability across services; future Prometheus.

## Scope
- Middleware to set/propagate `X-Request-ID`.
- Include ID in structured logs.
- `/metrics` endpoint stub (200).

## Acceptance Criteria
- Request ID present in logs across hops.
- Metrics endpoints return 200 (content TBD).

## Branch
feat/observability-v1
MD

open_issue "Docker secrets integration for LOG_TOKEN (dev path)" \
"type/security,priority/P1" <<'MD'
## Why
Move from envs to Docker secrets for sensitive values.

## Scope
- Compose `secrets:` for `log_token`.
- Services read `LOG_TOKEN_FILE`.
- Provide dev script to generate secrets in `secrets/`.

## Acceptance Criteria
- Stack boots with mounted secret; no secrets in git.

## Branch
sec/docker-secrets
MD

open_issue "Profiles & prod overlay" \
"type/infra,priority/P2" <<'MD'
## Why
Toggle optional services and prep for prod.

## Scope
- Compose profiles (e.g., `ui`, `workers`).
- Prod compose overlay (no bind mounts, resource limits).
- Document `--profile` usage.

## Acceptance Criteria
- `--profile ui` spins frontend; prod overlay builds and runs.

## Branch
ops/profiles-and-prod
MD

open_issue "Log sink: Loki or S3 object-lock (choose one)" \
"type/runtime,priority/P2,area/log_indexer" <<'MD'
## Why
Durable, queryable logs and/or tamper-evident storage.

## Scope (choose path):
- Loki: add Promtail or direct push; basic dashboard doc.
- S3: append-only NDJSON + object lock; export API.

## Acceptance Criteria
- Logs visible in chosen sink; export tested.

## Branch
feat/log-sink
MD

# --------------------------- PR TEMPLATE ---------------------------

mkdir -p .github
cat > .github/pull_request_template.md <<'PR'
## Summary
<!-- What changed and why. Keep it tight. -->

## Changes
- [ ] 

## Acceptance Criteria
- [ ] Local build passes
- [ ] `docker compose up -d` → all services healthy in <60s (attach `compose ps` or logs)
- [ ] Endpoint proof (e.g., `/api/ready` 200)
- [ ] Security invariants preserved (non-root, pinned base, no secrets in repo)

## Testing Evidence
<!-- Paste curl outputs, screenshots, or logs -->

## Risk & Rollback
<!-- What could break, and how to revert safely -->
PR

echo "Done. Labels, issues, and PR template created."
