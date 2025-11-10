# Telemetry Retention & Evidence Spine Export

## Pipeline overview

Foundry telemetry now flows through a shared set of infrastructure components:

1. **Producers** (for example the orchestrator service) publish JSON payloads to NATS on the
   `arescore.foundry.telemetry` subject using the shared telemetry client.
2. **Audit Collector** subscribes to the same subject and writes newline-delimited JSON (JSONL) files to
   `audits/foundry-events.jsonl` inside the repository directory that is bind-mounted into the container.
3. **Loki** and **MinIO** are available in the compose stack for centralised log aggregation and object
   retention respectively. Loki can be pointed at the audit collector logs, while MinIO is the preferred
   target for durable event archives.
4. **DuckDB** tooling is provided (via `docker compose run duckdb`) to generate Parquet exports for the
   Evidence Spine and to perform ad-hoc analysis.

The services are defined in `compose.yml`. Run `docker compose up -d nats audit_collector orchestrator` to
start the minimum viable telemetry stack.

## Retention policy

The JSONL sink (`audits/foundry-events.jsonl`) should be rotated on a 30-day cadence. In development
setups the file is stored on the host filesystem and can be rotated using standard logrotate rules. For
longer-term retention:

- Ship the JSONL file (or the Parquet export described below) to the MinIO bucket `foundry-audit` using the
  MinIO console at http://localhost:9001 or the `mc` CLI.
- Tag uploads with ISO8601 timestamps so downstream automation can expire buckets older than the retention
  horizon.
- Keep a single rolling archive in MinIO and prune on the same 30-day schedule.

## Export to the AresCore Evidence Spine (stub)

Until the Evidence Spine ingestion API is finalised, the export workflow is:

1. Generate a Parquet snapshot alongside the JSONL file:

   ```bash
   ./scripts/audit_report.sh
   ```

   This writes `audits/foundry-events.parquet` and prints a summary of event counts.

2. Upload the Parquet file to MinIO under `foundry-audit/exports/` for hand-off to the Evidence Spine team.
3. Record metadata (export timestamp, git commit, and operator) in the Evidence Spine backlog.

Once the backend is ready the above step will be replaced with an authenticated `curl`/`mc` invocation that
posts the Parquet artifact directly to the Evidence Spine ingestion endpoint. A stub shell function is kept in
`scripts/audit_report.sh` to make it easy to plug the new command in later.

## Operational notes

- The audit collector honours `FOUNDRY_TELEMETRY_PATH` if you want to redirect output to a different volume.
- Restarting the collector is safe; NATS delivers messages at-least-once and DuckDB scripts can be re-run to
  regenerate Parquet exports.
- Use `./scripts/audit_smoke.sh` after any infrastructure change to confirm telemetry still flows end-to-end.
