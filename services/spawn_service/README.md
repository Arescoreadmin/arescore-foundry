# Spawn Service

The spawn service is a FastAPI application responsible for managing multi-tenant
training scenarios. It exposes tenancy CRUD APIs, validates spawn requests with
Open Policy Agent (OPA), verifies JWT access tokens (with a development bypass),
and drives orchestrator interactions to launch new training sessions.

## Features

- **Health**: `/health`, `/live`, `/ready` for liveness checks.
- **Tenancy management**: `/api/tenants`, `/api/plans`, `/api/users`, and
  `/api/templates` provide CRUD endpoints for tenants, plans, users, and
  scenario templates.
- **Scenario spawning**: `/api/spawn` provisions a new orchestrator scenario
  after verifying plan quotas and policy constraints via OPA.
- **JWT authentication**: Incoming requests must present a bearer token. For
  local workflows, set `DEV_BYPASS_TOKEN` (default `DEV-LOCAL-TOKEN`) and use
  that value as the bearer token to assume the demo tenant.
- **PostgreSQL storage**: SQLAlchemy models and Alembic migrations manage all
  persistent data, including demo seed data.

## Configuration

Configuration is provided through environment variables (defaults shown):

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://spawn_service:spawn_service@localhost:5432/spawn_service` |
| `ORCHESTRATOR_URL` | Base URL of the orchestrator service | `http://orchestrator:8080` |
| `ORCHESTRATOR_SCENARIOS_PATH` | Orchestrator endpoint for new scenarios | `/api/scenarios` |
| `CONSOLE_BASE_URL` | Base URL used to build scenario access links | `https://mvp.local/console` |
| `OPA_URL` | Base URL for the OPA sidecar | `http://opa:8181` |
| `OPA_POLICY_PATH` | Policy path used for spawn authorization | `/v1/data/spawn/allow` |
| `JWT_SECRET` | Symmetric signing secret for JWT validation | _required for non-dev tokens_ |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_AUDIENCE` | Expected JWT audience (optional) | — |
| `JWT_ISSUER` | Expected JWT issuer (optional) | — |
| `DEV_BYPASS_TOKEN` | Development shortcut token value | `DEV-LOCAL-TOKEN` |
| `DEMO_TENANT_ID` | UUID for the seeded demo tenant | `00000000-0000-0000-0000-000000000001` |
| `DEMO_PLAN_ID` | UUID for the seeded demo plan | `00000000-0000-0000-0000-000000000010` |
| `DEMO_TEMPLATE_ID` | UUID for the seeded demo template | `00000000-0000-0000-0000-000000000100` |

## Database migrations & seed data

Alembic configuration is located under `app/alembic`. To run migrations:

```bash
alembic -c app/alembic.ini upgrade head
```

The initial migration (`20240528_0001_init`) creates all tables and seeds a demo
plan, tenant, and scenario template that align with the development bypass
token. Rerun migrations after updating models to keep the schema synchronized.

## OpenAPI surface

The FastAPI app automatically exposes OpenAPI documentation at `/openapi.json`
and an interactive UI at `/docs`. The following table mirrors the generated
endpoints for quick reference:

| Method | Path | Summary |
| --- | --- | --- |
| GET | `/health` | Service health indicator |
| GET | `/live` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/api/plans` | List plans |
| POST | `/api/plans` | Create plan |
| GET | `/api/plans/{plan_id}` | Retrieve plan |
| PUT | `/api/plans/{plan_id}` | Update plan |
| DELETE | `/api/plans/{plan_id}` | Delete plan |
| GET | `/api/tenants` | List tenants |
| POST | `/api/tenants` | Create tenant |
| GET | `/api/tenants/{tenant_id}` | Retrieve tenant |
| PUT | `/api/tenants/{tenant_id}` | Update tenant |
| DELETE | `/api/tenants/{tenant_id}` | Delete tenant |
| POST | `/api/tenants/{tenant_id}/plans/{plan_id}` | Assign plan to tenant |
| GET | `/api/users` | List users |
| POST | `/api/users` | Create user |
| GET | `/api/users/{user_id}` | Retrieve user |
| PUT | `/api/users/{user_id}` | Update user |
| DELETE | `/api/users/{user_id}` | Delete user |
| GET | `/api/templates` | List scenario templates |
| POST | `/api/templates` | Create scenario template |
| GET | `/api/templates/{template_id}` | Retrieve scenario template |
| PUT | `/api/templates/{template_id}` | Update scenario template |
| DELETE | `/api/templates/{template_id}` | Delete scenario template |
| POST | `/api/spawn` | Spawn scenario with OPA enforcement |

For detailed request/response schemas, consult the `/docs` page while the
service is running.
