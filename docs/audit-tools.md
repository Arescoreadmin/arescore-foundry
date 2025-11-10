# Foundry audit & telemetry tools

## JSONL sink

Orchestrator telemetry is written as JSONL to:

- `audits/foundry-events.jsonl`

Each line is a JSON object with:

- `event`: event kind (e.g. `scenario.created`)
- `payload`: event payload (scenario metadata, etc.)
- `timestamp`: ISO8601 timestamp (UTC)

The file path can be overridden via `FOUNDRY_TELEMETRY_PATH` and is automatically
mounted into the telemetry collector stack described below.

## Telemetry collector stack

Foundry ships a lightweight observability overlay that tails the JSONL sink and
indexes it in [Grafana Loki](https://grafana.com/oss/loki/) via Promtail. Enable
the stack when starting compose:

```bash
USE_TELEMETRY=1 make up
```

Services included in the overlay:

| Service    | Purpose                                            | Ports |
| ---------- | -------------------------------------------------- | ----- |
| `loki`     | Durable log store with 7-day retention             | 3100  |
| `promtail` | Ships JSONL audit events into Loki                 | —     |
| `grafana`  | Quick dashboards + log explorer (`admin/admin`)    | 3001  |

Promtail labels events with `event`, `scenario_id`, `template`, and `tenant_id`
which makes it trivial to build saved queries in Grafana Explore. The default
Grafana endpoint lives at `http://localhost:3001/` (credentials `admin` /
`admin`).

## Smoke checks

### `scripts/audit_smoke.sh`

Runs against a local stack (orchestrator + spawn + OPA):

- Spawns a `netplus-demo` scenario via `single_site_scenario_create.sh`
- Verifies that at least one `scenario.created` event exists in
  `audits/foundry-events.jsonl`
- Prints a short summary if events are present

### `scripts/audit_report.sh`

Summarizes existing telemetry and supports quick filtering:

```bash
# full summary
./scripts/audit_report.sh

# only show the last 20 scenario.created events from the last six hours
./scripts/audit_report.sh --event scenario.created --since 6h --show-events

# emit raw JSON for all events for a specific tenant
audit_target="2024-05-01T00:00:00Z"
./scripts/audit_report.sh --event scenario.created --event scenario.completed \
  --since "$audit_target" --output json --limit 0
```

Flags of note:

- `--event/-e`: filter on one or more event kinds.
- `--since`: accepts ISO8601 timestamps or relative durations (`15m`, `2h`,
  `3d`).
- `--show-events`: print the matching events either as text (default) or JSON.
- `--limit`: cap how many events are rendered when `--show-events` is set (`0`
  prints all).
