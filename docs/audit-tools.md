# Foundry audit & telemetry tools

## JSONL sink

Orchestrator telemetry is written as JSONL to:

- `audits/foundry-events.jsonl`

Each line is a JSON object with:

- `event`: event kind (e.g. `scenario.created`)
- `payload`: event payload (scenario metadata, etc.)
- `timestamp`: ISO8601 timestamp (UTC)

## Smoke checks

### `scripts/audit_smoke.sh`

Runs against a local stack (orchestrator + spawn + OPA):

- Spawns a `netplus-demo` scenario via `single_site_scenario_create.sh`
- Verifies that at least one `scenario.created` event exists in `audits/foundry-events.jsonl`
- Prints a short summary if events are present

### `scripts/audit_report.sh`

Summarizes existing telemetry:

```bash
./scripts/audit_report.sh
