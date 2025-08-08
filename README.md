# Sentinel Foundry MVP

This repository contains a minimal, modular proof of concept for Sentinel Foundry. Each service is containerized and communicates over HTTP.

## Services
- **Orchestrator** – coordinates sessions and proxies calls to AI modules.
- **Sentinel Core** – blue‑team defensive agent.
- **Sentinel Red** – red‑team attacking agent.
- **Log Indexer** – tamper‑evident log service.

## Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Start the stack with Docker:
   ```bash
   docker compose up --build
   ```

The stack exposes:
- Orchestrator on `localhost:8000`
- Sentinel Core on `localhost:8001`
- Sentinel Red on `localhost:8002`
- Log Indexer on `localhost:8003`

Each service provides a `/health` endpoint for basic monitoring.
