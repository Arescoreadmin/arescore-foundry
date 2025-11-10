# FrostGate Foundry — Train Where the Machines Learn You.

FrostGate Foundry is a **multi-tenant, agentic cyber-range SaaS** evolved from the Sentinel Foundry blueprint and AresCore’s federated spine.  
It transforms certification prep, AI safety testing, and cyber-defense into a cinematic, policy-governed training universe — where learners, agents, and adversaries evolve together.

---

## 0. Quick Start

```bash
cp infra/.env.example infra/.env
ENV_FILE="$(pwd)/infra/.env" make up   # or: docker compose --env-file infra/.env up --build
```

Health checks
- Orchestrator API: http://localhost:8080/health
- Spawn service (from inside the container): `docker compose exec spawn_service curl -s http://localhost:8080/health`

Spawn smoke:
```bash
docker compose exec spawn_service \
  curl -sX POST http://localhost:8080/api/spawn \
    -H 'authorization: Bearer DEV-TENANT-TOKEN' \
    -d '{"track":"netplus","tenant_id":"demo-tenant"}'
```

---

## 1. Core Philosophy

Foundry isn’t a simulator. It’s a **parallel digital world** where FrostGate’s logic, policy, and AI can be trained, tested, and governed — safe, adaptive, and fully auditable.

---

## 2. Architecture Overview

| Layer | Responsibility | Tech |
| --- | --- | --- |
| Spawn Service | SaaS entrypoint; auth, billing, quota enforcement | FastAPI + OPA |
| Orchestrator | Spins up sandbox topologies, manages lifecycle | FastAPI + Docker SDK + NATS |
| Ingestor Services | Mirror FrostGate Core identity / incidents / telemetry | Independent microservices |
| Governance Engine | Policy definition & enforcement | OPA + Rego |
| Reasoner / Agentic | Plan→Retrieve→Act→Reflect learning loop | RAG + Vector DB |
| Telemetry Bus | Streams events | NATS / Loki / Redis Stream |
| Audit Subsystem | JSONL → Parquet evidence | Loki + DuckDB/Trino |
| Portal UI | Tenant dashboards & cinematic UX | Next.js + Tailwind + shadcn |
| DevOps | CI/CD + infra templates | GitHub Actions + Terraform |
| Storage | Durable state & payloads | Postgres + MinIO + Elasticsearch |

All services are containerized and communicate via APIs or queues — no shared deps.

---

## 3. SaaS Model

| Entity | Description |
| --- | --- |
| **Tenant** | Paying organization; owns data & quotas |
| **Plan** | Seat, feature, and concurrency limits |
| **User** | Learner / Instructor / Admin |
| **TrainingSession** | Single sandbox lifecycle |
| **ScenarioTemplate** | Versioned topology + policy definition |

Each table is keyed by `tenant_id`.  
Control Plane handles tenants, billing, and spawn orchestration; Range Plane runs sandboxes.

---

## 4. Federation Layers

### 4.1 AresCore Federated Model & Evidence Spine
- Services: `fl_aggregator`, `fl_coordinator`, `model_registry`, `consent_registry`, `evidence_bundler`
- Federates **models, metrics, and evidence**, not raw data
- Foundry ships signed **AuditPacks** to the spine
- CRL-based revocation & rollback

### 4.2 Foundry Cluster Federation (Deployment)
- Control plane per region; range clusters per tenant or geography
- Aggregated observability and governance
- Range isolation preserved

> **AresCore Federation** = learning & proof  
> **Foundry Federation** = deployment & management

---

## 5. Identity & Topology Mirror (FrostGate Core)

### Canonical Models

**Site**
| Column | Type |
| --- | --- |
| site_id | UUID PK |
| tenant_id | UUID FK |
| name | TEXT |
| type | ENUM(hq, branch, dc, home, edge) |
| region | TEXT |
| active_snapshot_id | UUID FK |

**NetworkSegment**
| Column | Type |
| --- | --- |
| segment_id | UUID PK |
| tenant_id | UUID FK |
| site_id | UUID FK |
| type | ENUM(lan, wireless, atm, mpls, sd-wan, cellular, iot_mesh, control, non_terrestrial) |
| transport_type | ENUM(internet, mpls, lte, satellite, overlay) |
| role | ENUM(trusted, guest, byod, iot, printer_only, backbone) |
| bandwidth_mbps | NUMERIC |
| latency_ms | NUMERIC |
| loss_pct | NUMERIC |
| mdns_policy | ENUM(allow, deny, proxy) |
| edge_node | BOOL |
| created_at / updated_at | TIMESTAMP |

**Device**
| device_id | UUID PK |
| tenant_id | UUID FK |
| site_id | UUID FK |
| mac | TEXT UNIQUE |
| fingerprints | JSONB |
| owner_user_id | UUID FK |
| role | ENUM(corp-mobile, byod, printer, iot, etc.) |
| status | ENUM(active, revoked, quarantine, pending) |
| connectivity_type | ENUM(wired, wireless, cellular, satellite) |
| last_seen_at | TIMESTAMP |

**Snapshot**
| snapshot_id | UUID PK |
| tenant_id | UUID FK |
| site_id | UUID FK |
| hash | TEXT |
| signature | TEXT |
| anchor_txid | TEXT |
| raw_payload_ref | TEXT |
| device_count | INT |
| ssid_count | INT |
| created_at | TIMESTAMP DEFAULT now() |

### Ingestor Services

- `foundry-identity-ingestor` – Sites & snapshots  
- `foundry-telemetry-ingestor` – Event feeds  
- `foundry-incident-ingestor` – Alerts/incidents  
- `foundry-topology-ingestor` – Netmaps  

Each exposes `/sync` and emits NATS events like:
```json
{"event":"snapshot.synced","tenant_id":"demo","site_id":"HQ01"}
```

---

## 6. Sandbox & Simulation Layer

### 6.1 Topology DSL

Supports **single or multi-topology** networks:

```yaml
scenario:
  id: netplus-branch-v1
  name: "Net+ Branch Fundamentals"
  complexity_tier: bronze
  routing_domains:
    - id: rd-campus
    - id: rd-branch
  topologies:
    - id: campus-main
      routing_domain: rd-campus
      segments:
        - name: campus-lan
          type: lan
          role: trusted
        - name: guest-wifi
          type: wireless
          role: guest
    - id: branch-1
      routing_domain: rd-branch
      segments:
        - name: branch-lan
          type: lan
          role: trusted
        - name: branch-wan
          type: mpls
          role: backbone
  interconnects:
    - from: campus-main.edge-fw
      to: branch-1.branch-wan
      type: ipsec_tunnel
      shaping:
        latency_ms: 80
        loss_pct: 0.3
  constraints:
    max_nodes: 80
    max_segments: 20
    max_routes: 512
```

Compiled to container network graphs via:
- Docker namespaces, bridges, veth pairs  
- `tc` / `netem` shaping  
- Nested or parameterized SD-WAN, satellite, IoT meshes

### 6.2 Scenario Lifecycle

**Template → Instance → State Machine**

- Template defines assets, policy, scoring  
- Instance spawns containers  
- State machine transitions on completion or violation  

Scenario types: LAN / Wi-Fi / ATM / MPLS / SD-WAN / IoT / Cellular / Satellite  
Each declares resource and complexity budgets.

---

## 7. Governance & Policy (OPA)

OPA guards every decision.

Example context:
```json
{"tenant":{"id":"demo"},"device":{"role":"byod"},"network":{"role":"trusted"}}
```

Example policy:
```rego
package training.gate
deny[msg] {
  input.device.role == "byod"
  input.network.role == "trusted"
  msg := "BYOD device on trusted network"
}
allow { not deny[_] }
```

Policy suites:
- `training_gate` – scenario governance  
- `fl_ingress` – data ingress  
- `authority` – agent permissions  
- `consent` – user/tenant consent  
- `runtime_revocation` – CRL-based kill switch

All logs flow to `audits/foundry-events.jsonl`.

---

## 8. Agentic Learning & Reasoner Layer

### Loop: Plan → Retrieve → Act → Reflect
- **Plan**: propose actions  
- **Retrieve**: audits + telemetry + identity context  
- **Act**: orchestrator ops (OPA-approved)  
- **Reflect**: update vector memory (`task_memory`)

### Components
- `foundry_reasoner` – reasoning loop  
- `performance_evaluator` – scoring + difficulty delta  
- `difficulty_controller` – scenario tuning  
- `intake_survey_ui` – learner baseline mapping  
- `leaderboard_service` – real-time scoring  
- `llm_analyzer` – gates AI-generated changes  
- `overlay_sanitizer` – prompt and data sanitization  

Agents respect strict step/time/resource budgets.

---

## 9. Telemetry & Audit

| Source | Transport | Sink |
| --- | --- | --- |
| Sandbox | NATS / Loki | JSONL audit store |
| OPA | HTTP hook | JSONL audit store |
| User | REST / WS | JSONL audit store |
| Agents | NATS | Audit + vector memory |

Audits compact → Parquet → DuckDB/Trino queries.  
Evidence exported to AresCore’s `evidence_bundler`.

Scripts: `audit_smoke.sh`, `audit_report.sh`.

---

## 10. Cinematic Experience & UI

### Views
- Dashboard (health, scores, policy hits)
- Training Console (Briefing → Mission → Debrief)
- Sites & Segments (live topology)
- Devices & Policy Conformance
- Audit Viewer
- Leaderboards (Platinum / Titanium / Steel / Cadet)

### Presentation
- YAML-driven narration (ElevenLabs / Coqui)
- Live telemetry HUD
- FrostGate rune theming
- WebSocket-driven state updates

---

## 11. Auth, Billing & Ops

- Tenant JWTs + optional SSO (OIDC/SAML)
- `billing_adapter` enforces seat/range quotas
- OPA spawn policies enforce plan caps

```bash
curl -X POST /api/spawn  -H 'Authorization: Bearer <tenant_token>'  -d '{"tenant_id":"demo","track":"netplus"}'
```

Response:
```json
{
  "session_id":"sess-001",
  "scenario_id":"scn-001",
  "access_url":"https://app.frostgatefoundry.com/c/sess-001"
}
```

---

## 12. CI/CD & Supply Chain

Pipelines:
- `foundry-smokes` – OPA + telemetry
- `build_push` – multi-arch container builds
- `audit-lint` – policy/schema validation
- `supplychain-gate` – SBOM + CVE scans

Local helpers:  
`foundry_smoke_all.sh`, `audit_smoke.sh`, `audit_report.sh`

All services run non-root and expose `/health`.

---

## 13. Deployment Modes

### Local
```bash
docker compose up -d --build
```

### Staging
```bash
docker compose  -f compose.yml  -f compose.staging.yml  -f compose.federated.yml up -d --build
```

### Cloud SaaS
- Control plane: `foundry-control` namespace  
- Range plane: `tenant-*` namespaces  
- Managed dependencies: Postgres, NATS, Loki, Prometheus, MinIO/S3  

---

## 14. Roadmap

| Phase | Focus | ETA |
| --- | --- | --- |
| 1 | Core models + OPA + multi-tenant base | 3 wks |
| 2 | Orchestrator + sandbox engine | 4 wks |
| 3 | Reasoner + telemetry pipeline | 3 wks |
| 4 | UI + cinematic layer | 3 wks |
| 5 | SaaS ops (billing, quotas) | 3 wks |
| 6 | Federation + advanced AI agents | 4–6 wks |

Full build: ~4–5 months (2 senior engineers)

---

## 15. Security & Governance

- Deny-all egress by default
- OPA everywhere (training, consent, revocation)
- Immutable signed audit chain
- CRL-based kill switches
- Continuous SBOM + CVE scanning
- CI gates for models, evidence, policies, and supply chain

---

## 16. FrostGate Core, FrostGate Spear, and Universal Sandbox Connector

### 16.1 FrostGate Core — Defender Intelligence Module
- Defensive AI handling anomaly detection & auto-remediation
- Consumes sandbox telemetry streams
- Produces policy suggestions, defense reports
- OPA-gated; emits signed decisions into the audit chain

### 16.2 FrostGate Spear — Adversarial Intelligence Module
- Successor to Sentinel Red
- Simulates offensive campaigns and adaptive adversaries
- Connects via `adversary_connector` in the Scenario Engine
- Modes:
  - Scripted (ATT&CK playbooks)
  - Autonomous (LLM/agentic)
- Feeds attack metrics into `performance_evaluator`

### 16.3 Universal Sandbox Connector (USC)
Generic connector for testing **any containerized software** inside Foundry’s governed sandbox.

| Feature | Description |
| --- | --- |
| Isolation | Per-test namespace / container stack |
| Policy Control | OPA `sandbox_connector.rego` restricts syscalls, net egress |
| Logging | stdout/stderr + net telemetry → Loki audit stack |
| Interface | REST/gRPC `connector_service` |
| Use Cases | Malware detonation, EDR validation, agent sandboxing, QA |

Example:
```json
{
  "tenant_id":"demo",
  "software_id":"test-app-001",
  "image":"registry.frostgate.io/test/app:latest",
  "policy_profile":"restricted",
  "purpose":"malware_analysis"
}
```
Response:
```json
{
  "sandbox_id":"sbx-8891",
  "access_url":"https://app.foundry/sbx-8891",
  "logs_url":"https://logs.foundry/sbx-8891"
}
```

**Purpose:**
- Unified substrate for training, red/blue collaboration, and software testing  
- Closed-loop: *Core defends → Spear attacks → Reasoner learns → Policies adapt*

### Data Flow
```
 [Sandbox Containers] → [Telemetry Bus] → [FrostGate Core]
                              ↘︎
                               [FrostGate Spear]
                              ↘︎
                             [Universal Connector]
                               ↓
                         [Reasoner + Evaluator]
                               ↓
                      [Audit + AresCore Evidence Spine]
```

---

## 17. License

© FrostGate Systems.  
Derived from Sentinel Foundry and AresCore Federated Spine under internal license.  
Third-party: FastAPI, Qdrant/Weaviate, OPA, NATS, Loki, Prometheus, Next.js, TailwindCSS.

---

### Tagline
**FrostGate Foundry — Train Where the Machines Learn You.**
