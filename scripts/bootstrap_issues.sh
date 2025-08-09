#!/usr/bin/env bash
set -euo pipefail

say() { printf "\n\033[1;36m==>\033[0m %s\n" "$*"; }

# -------- Detect repo --------
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) not found. Install: https://cli.github.com/"; exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated. Run: gh auth login"; exit 1
fi

REPO="${REPO:-}"
if [ -z "${REPO}" ]; then
  if ! REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)"; then
    echo "ERROR: Cannot detect repo. Set REPO=owner/name then re-run."; exit 1
  fi
fi
say "Using repository: ${REPO}"

# -------- Create labels (idempotent) --------
mklabel() {
  local name="$1" color="$2" desc="$3"
  if gh label view "$name" --repo "$REPO" >/dev/null 2>&1; then
    gh label edit "$name" --color "$color" --description "$desc" --repo "$REPO" >/dev/null
  else
    gh label create "$name" --color "$color" --description "$desc" --repo "$REPO" >/dev/null
  fi
}

say "Creating/updating labels..."
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
say "Labels ready."

# -------- Helper to create issues only if not already present --------
open_issue() {
  local title="$1"; shift
  local labels_csv="$1"; shift
  local body="$*"

  if gh issue list --repo "$REPO" --search "in:title \"$title\"" --state all --json title -q 'length(.)' | grep -q '^0$'; then
    say "Creating issue: $title"
    gh issue create --repo "$REPO" --title "$title" --label "$labels_csv" --body "$body" >/dev/null
  else
    say "Issue already exists, skipping: $title"
  fi
}

# ---------------- P0: FIX BROKEN STUFF ----------------


open_issue "Finalize /api proxy via Nginx (no CORS) + runtime config" \
"type/infra,priority/P0,area/frontend" \
"## Why
Keep single-origin dev/prod, avoid CORS.

## Scope
- frontend/nginx.conf: location /api/ { proxy_pass http://orchestrator:8000/; ... }
- frontend/public/config.js: API_BASE='/api'.
- Rebuild frontend image.

## Acceptance
- nginx -t passes in container.
- curl http://localhost:3000/api/ready returns orchestrator JSON (not HTML).

## Branch
feat/proxy-stable
"

open_issue "Add /ready to all services + compose healthchecks + restart policies" \
"type/runtime,priority/P0,area/orchestrator,area/log_indexer,area/frontend" \
"## Why
Uniform readiness + auto-recovery; avoid startup coupling.

## Scope
- Add @app.get('/ready') to services (frontend served by Nginx—/ already 200).
- Compose: healthcheck hits /ready; restart: unless-stopped.
- Remove unnecessary depends_on.

## Acceptance
- Kill/restart any single container → recovers to healthy.
- docker compose ps shows healthy.

## Branch
feat/health-ready-everywhere
"

open_issue "Orchestrator healthcheck support (curl or Python)" \
"type/infra,priority/P0,area/orchestrator" \
"## Why
HEALTHCHECK used curl which wasn’t installed.

## Scope
- Install curl in orchestrator image OR switch to Python-based check.
- Keep pinned base and non-root.

## Acceptance
- Orchestrator becomes healthy within 40s of start.
- Dockerfile shows pinned base and non-root.

## Branch
chore/orchestrator-healthcheck-tools
"

open_issue "Run as non-root + pinned base images across services" \
"type/security,priority/P0,area/orchestrator,area/log_indexer,area/frontend" \
"## Why
Hardening and predictable builds.

## Scope
- python:3.11-slim, node:18-alpine, nginx-unprivileged:stable-alpine.
- Add non-root users (USER appuser), fix ownership.
- Keep HEALTHCHECKs.

## Acceptance
- docker compose run --rm orchestrator id -u ≠ 0 (same for others).
- Images build clean; services start healthy.

## Branch
sec/nonroot-pins
"

open_issue "Structured logging emitter to log_indexer (non-blocking)" \
"type/runtime,priority/P0,area/orchestrator,area/log_indexer" \
"## Why
LOG_* envs exist but we don’t emit logs.

## Scope
- Add log.py helper (async httpx + timeout/backoff).
- Emit startup and request events with {ts, svc, evt, request_id}.
- Best-effort: failures don’t block.

## Acceptance
- Logs appear in log_indexer with hash chain.
- When indexer is down, API still responds; when back up, logs resume.

## Branch
feat/logging-emitter
"

open_issue "Remove plaintext defaults; support *_FILE secrets" \
"type/security,priority/P0,area/orchestrator,area/log_indexer" \
"## Why
Eliminate changeme-* in code; prepare for Docker secrets.

## Scope
- No default secrets in code; env or *_FILE only.
- Add .env.example (placeholders only).
- Compose accepts secrets: in follow-up issue.

## Acceptance
- git grep -n 'changeme' → 0 hits.
- Services run with envs; docs updated.

## Branch
sec/secrets-envfile-stage1
"

# ---------------- P1+: UPGRADES ----------------

open_issue "CI supply-chain gates: SBOM + Trivy + Dockerfile lint" \
"type/ci,priority/P1" \
"## Why
Block regressions & vulnerable images.

## Scope
- GitHub Actions: buildx, Syft SBOM, Trivy scan (fail on HIGH/CRITICAL), Hadolint.
- Upload SBOM artifact; status checks required on PRs.
- Optionally push to GHCR on main.

## Acceptance
- PRs blocked when scan fails.
- SBOM artifact published.

## Branch
ci/supply-chain
"

open_issue "Observability v1: X-Request-ID + basic /metrics placeholders" \
"type/runtime,priority/P1" \
"## Why
Traceability across services; future Prometheus.

## Scope
- Middleware to set/propagate X-Request-ID.
- Include ID in structured logs.
- /metrics endpoint stub (200).

## Acceptance
- Request ID present in logs across hops.
- Metrics endpoints return 200.

## Branch
feat/observability-v1
"

open_issue "Docker secrets integration for LOG_TOKEN (dev path)" \
"type/security,priority/P1" \
"## Why
Move sensitive values to Docker secrets.

## Scope
- Compose secrets: for log_token.
- Services read LOG_TOKEN_FILE.
- Provide dev script to generate secrets in secrets/.

## Acceptance
- Stack boots with mounted secret; no secrets in git.

## Branch
sec/docker-secrets
"

open_issue "Profiles & prod overlay" \
"type/infra,priority/P2" \
"## Why
Toggle optional services and prep for prod.

## Scope
- Compose profiles (e.g., ui, workers).
- Prod compose overlay (no bind mounts, resource limits).
- Document --profile usage.

## Acceptance
- --profile ui spins frontend; prod overlay builds and runs.

## Branch
ops/profiles-and-prod
"

open_issue "Log sink: Loki or S3 object-lock (choose one)" \
"type/runtime,priority/P2,area/log_indexer" \
"## Why
Durable, queryable logs and/or tamper-evident storage.

## Scope (choose path):
- Loki: add Promtail or direct push; basic dashboard doc.
- S3: append-only NDJSON + object lock; export API.

## Acceptance
- Logs visible in chosen sink; export tested.

## Branch
feat/log-sink
"

# -------- PR template (written locally; you commit it) --------
say "Writing PR template locally (.github/pull_request_template.md)"
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

say "Done. Labels & issues created in ${REPO}. PR template written locally (commit it)."
