# FrostGate Foundry Starter Project

## Getting Started

1. Copy `.env.example` to `.env` and set your API keys.

1. Build and run all containers:

```bash
docker-compose up --build
```

3. Access the frontend at http://localhost:3000

## Services

- Orchestrator: manages session and worlds
- FrostGateCore: defender AI module
- FrostGateRed: attacker AI module
- MutationEngine: evolves AI strategies
- LogIndexer: central logging service
- BehaviorAnalytics: analyzes behavior and alerts
- Frontend: React dashboard

## Notes

- All services expose `/health` endpoint for health checks.
- Environment variables control API keys and configs.
- Use non-root users in Dockerfiles for security.

## Telemetry & Auditing

- `compose.yml` now provisions NATS, Loki, MinIO, the audit collector, and DuckDB tooling for local
  experimentation. Start the core stack with `docker compose up -d nats audit_collector orchestrator`.
- JSONL audit trails live under `audits/foundry-events.jsonl`; use `./scripts/audit_report.sh` to summarise
  events and export Parquet snapshots for further analysis.
- Retention guidance and the hand-off process to the AresCore Evidence Spine are documented in
  [`docs/audit-retention.md`](docs/audit-retention.md).

### Local run

1. `cp infra/.env.example infra/.env` and adjust values.
2. `make up` to build & start everything.
3. Health:
   - API: http://localhost:8000/health
   - Frontend: http://localhost:3000/health
4. Rebuild just the UI after env/UI changes: `make rebuild-frontend`
5. Stop/clean: `make down`
