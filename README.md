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

### Local run

1. `cp infra/.env.example infra/.env` and adjust values.
2. `make up` to build & start everything.
3. Health:
   - API: http://localhost:8000/health
   - Frontend: http://localhost:3000/health
4. Rebuild just the UI after env/UI changes: `make rebuild-frontend`
5. Stop/clean: `make down`

## 13. Deployment playbooks

The deployment flow is split between the **control-plane** (OPA, orchestrator, spawn, NATS) and the **range-plane** (tenant workloads, MinIO, Loki, ingestors, federated services). Use the compose overlays and IaC templates below to target each slice.

### Local bootstrap

```bash
# bring up control + range plane locally (build-from-source)
docker compose --profile control-plane --profile range-plane \
  -f compose.yml -f compose.federated.yml up --build

# tear down
docker compose --profile control-plane --profile range-plane \
  -f compose.yml -f compose.federated.yml down -v
```

### Staging control-plane

```bash
# use published container images for the control-plane only
docker compose --profile control-plane \
  -f compose.yml -f compose.staging.yml up -d opa nats orchestrator spawn_service

# deploy Kubernetes namespace + config via Terraform
terraform -chdir=infra/terraform/control-plane init
terraform -chdir=infra/terraform/control-plane apply -auto-approve

# render the Helm namespace scaffolding (dry-run) before applying
helm upgrade --install control-plane infra/helm/control-plane \
  --namespace foundry-control --create-namespace --dry-run
```

### Cloud / tenant range-plane

```bash
# start range-plane services + federated workers using remote control-plane endpoints
docker compose --profile range-plane \
  -f compose.yml -f compose.federated.yml up -d ingestors loki minio fl_coordinator consent_registry evidence_bundler

# provision tenant namespaces with Terraform
terraform -chdir=infra/terraform/tenant-range init
terraform -chdir=infra/terraform/tenant-range apply -auto-approve

# stamp tenant namespaces + quotas with Helm
helm upgrade --install range-plane infra/helm/range-plane \
  --namespace foundry-system --create-namespace --dry-run
```

> ℹ️ Customize image registries by exporting `GITHUB_REPOSITORY_LC` (for Compose overlays) and tenant metadata through the Terraform/Helm value files.
