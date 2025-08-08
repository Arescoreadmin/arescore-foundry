# Sentinel Foundry Starter Project

## Getting Started

1. Copy `.env.example` to `.env` and set your API keys.

2. Build and run all containers:

```bash
docker-compose up --build
```

3. Access the frontend at http://localhost:3000

## Services

- Orchestrator: manages session and worlds
- SentinelCore: defender AI module
- SentinelRed: attacker AI module
- MutationEngine: evolves AI strategies
- LogIndexer: central logging service
- BehaviorAnalytics: analyzes behavior and alerts
- Frontend: React dashboard

## Notes

- All services expose `/health` endpoint for health checks.
- Environment variables control API keys and configs.
- Use non-root users in Dockerfiles for security.
