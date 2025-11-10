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
- Runtime Revocation Service: ingests CRLs and feeds OPA policy data
- Frontend: React dashboard

## Notes

- All services expose `/health` endpoint for health checks.
- Environment variables control API keys and configs.
- Use non-root users in Dockerfiles for security (enforced across all services).
- Review the hardening guide in [`docs/security/security-posture.md`](docs/security/security-posture.md) for network controls, revocation workflows, and incident response procedures.

### Local run

1. `cp infra/.env.example infra/.env` and adjust values.
2. `make up` to build & start everything.
3. Health:
   - API: http://localhost:8000/health
   - Frontend: http://localhost:3000/health
4. Rebuild just the UI after env/UI changes: `make rebuild-frontend`
5. Stop/clean: `make down`
