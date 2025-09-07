# Sentinel Forge — Architecture (MVP sprint)

## Core Principles
- **No monoliths.** Every feature is a container. No shared imports.
- **API or bus only.** REST/gRPC/Redis/NATS. No in-process coupling.
- **Fail-open.** Any service can die without halting others.
- **Forensic logging.** JSON logs → LogIndexer → tamper-evident hashing.
- **Zero secrets in code.** `.env` for local dev only; CI injects secrets.

## Services (initial)
- **orchestrator** (FastAPI): auth, routing, policy, runbooks. Port `8000`.
- **sentinelcore** (FastAPI): Defense AI (analysis, scoring, mitigations). Port `8001`.
- **sentinelred** (FastAPI): Red-team simulator (opt-in). Port `8002`.
- **behavior_analytics** (FastAPI): UEBA / anomaly detection. Port `8003`.
- **quarantine_engine** (FastAPI): Process/file isolation actions. Port `8004`.
- **notification_dispatcher** (FastAPI): Email/SMS/webhooks. Port `8005`.
- **self_healing_supervisor** (Python): watches healthbeats, restarts containers.
- **log_indexer** (Fluent Bit → Loki/ELK): ingest + redact + sign logs.
- **frontend** (Next.js): Operator UI. Port `3000`.
- **redis**: message bus; **nats** optional later.

## Network & Contracts
- All services expose:
  - `GET /health` (liveness), `GET /ready` (readiness)
  - `POST /log` (internal; bearer token `LOG_TOKEN`), JSON body `{ts, svc, lvl, evt, fields}`
- **Auth**: Bearer tokens from orchestrator. No cross-service trust.
- **Quarantine Engine contract**:
  - `POST /quarantine` `{entity_type, id, reason, policy_id}` → `{status, ticket_id}`
- **Notification contract**:
  - `POST /notify` `{channel, to, template, vars}` → `{queued: true, id}`

## Logging & Audit
- Services log structured JSON:
  - `{"ts":"ISO8601","svc":"sentinelcore","lvl":"INFO","evt":"anomaly_scored","score":0.91,"trace":"..."}`
- Redaction map (env `REDACT_KEYS` = `password,token,apikey,secret`).
- LogIndexer:
  - Computes SHA-256 chain `prev_hash -> hash` for tamper evidence.
  - Periodic anchor (optional) to external timestamping.

## Security Baseline
- Run as non-root UID, minimal base image, read-only FS (except `/tmp`).
- No outbound internet in prod containers except:
  - orchestrator → notify/log
  - notification_dispatcher → providers
- SBOM + image scan in CI (Trivy).
- Dependency pinning with `requirements.txt` / `package-lock.json`.

## Health & Self-Healing
- Docker healthchecks probe `/ready`. Supervisor listens on Docker API socket (read-only) and restarts unhealthy containers with exponential backoff.

## Configuration
- `.env.example` documents all vars. Local `.env` ignored by git.
- Required env (per service): `PORT`, `LOG_ENDPOINT`, `LOG_TOKEN`, `JWT_ISSUER`, `JWT_AUD`, `SERVICE_TOKEN`.

## CI/CD
- GitHub Actions:
  - Lint, typecheck, unit tests
  - Build images (multi-stage), Trivy scan, SBOM upload
  - Require green checks to merge

## Observability
- Request/response IDs via header `X-Trace-Id` (propagate across services).
- Basic metrics at `/metrics` (Prometheus).

## MVP “Golden Path” (E2E)
1) `/defend` (sentinelcore) scores synthetic event → mitigation
2) orchestrator records decision → LogIndexer
3) optional: quarantine_engine acts → notification_dispatcher alerts
