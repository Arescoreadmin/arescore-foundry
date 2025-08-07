# Sentinel Foundry

Composable, modular stack for Sentinel services.

## Setup

1. Copy `infra/.env.example` to `infra/.env` and set real values.
2. Run `scripts/start.sh` or `docker compose -f infra/docker-compose.yml --env-file infra/.env up -d`.
3. Access the dashboard at `http://localhost:3000`.

## Logging

All logs are sent to the `log_indexer` service and stored in the `log_data` volume. **Do not delete this volume** to preserve audit history.

## Security

All inter-container requests use a bearer token defined in the environment. Never hardcode secrets; manage them via environment files or a secrets manager.

## Services

- `orchestrator`: manages worlds and coordinates modules.
- `sentinelcore`, `sentinelred`, `mutation_engine`: pluggable AI modules.
- `log_indexer`: central log collection and export.
- `frontend`: React dashboard.

## Tests

Run `pytest` to execute integration checks.
