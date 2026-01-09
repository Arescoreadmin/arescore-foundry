# FROSTGATE FOUNDRY — FULL SYSTEM BLUEPRINT
## Train Where the Machines Learn You

---

## 1. Purpose

FrostGate Foundry is a **multi-tenant, policy-governed, agentic cyber-range SaaS**
designed to train humans, test AI systems, and produce auditable evidence of
decisions, behavior, and outcomes.

Foundry operates under one governing principle:

> **TRUST, BUT VERIFY**
> Every action must be gated by policy, logged, scored, and provable.

This document describes the **complete end-state system**.
It is **not** a build contract.

---

## 2. System Planes

### Control Plane
- Tenant management
- Authentication and authorization
- Quotas and billing enforcement
- Campaign scheduling
- Policy enforcement (OPA)

### Range Plane
- Sandbox orchestration
- Network topology execution
- Adversarial and defensive agents
- Telemetry emission

### Evidence & Learning Plane
- Telemetry aggregation
- AuditPack generation
- Offline learning and evaluation
- Federation with AresCore spine

---

## 3. Core Services

| Service | Responsibility |
|------|----------------|
| spawn_service | SaaS entrypoint, auth, quotas |
| orchestrator | Build and tear down sandboxes |
| campaign_scheduler | Continuous battle execution |
| telemetry_collector | Authoritative event ingestion |
| evidence_bundler | Deterministic AuditPack export |
| reasoner | Plan → Act → Reflect loop |
| evaluator | Scoring and outcome |
| difficulty_controller | Adaptive tuning |
| leaderboard_service | Competitive metrics |
| foundry_training | Offline learning jobs |
| consent_registry | Federated consent |
| model_registry | Versioned models |
| fl_coordinator | Federated learning spine |

All services are containerized and communicate via APIs or queues only.

---

## 4. Sandbox Engine

- Topology DSL → runtime graph
- Docker / Kubernetes execution
- Namespaces, bridges, veth pairs
- `tc/netem` shaping
- Resource budgets enforced
- Hard kill via policy revocation

---

## 5. Governance

- OPA deny-by-default
- Spawn gating
- Runtime action approval
- Training consent
- Ethics enforcement
- CRL-based revocation

No action executes without policy approval.

---

## 6. Telemetry & Evidence

- All actions emit events
- Authoritative store: JSONL
- Derived views: Loki, Parquet, DuckDB
- EvidencePack:
  - deterministic serialization
  - SHA256 hash
  - optional signature
  - federation export

---

## 7. Agentic Systems

- FrostGate Core (Defender)
- FrostGate Spear (Adversary)
- Reasoner loop with strict budgets:
  - time
  - steps
  - resources
- Drift detection and rollback

---

## 8. Federation

- Models, metrics, and evidence only
- No raw data sharing
- Consent and revocation enforced
- Evidence spine anchoring

---

## 9. User Interface

- Dashboards
- Live battle HUD
- Audit viewer
- Leaderboards
- Campaign controls

---

## 10. Operations

- Dev / Staging / Prod environments
- Nightly maintenance window
- CI/CD with policy gates
- Supply-chain security

---

## 11. Scope Tiers

| Tier | Description |
|---|---|
| MVP | Single-track cyber range with audit and scoring |
| MVP 2.0 | Offline learning and adaptive difficulty |
| Full Build | Federation, multi-hat curricula, cinematic UX |

---

## 12. Timeline

Estimated full build: **4–5 months**
Minimum staffing: **2 senior engineers**

---

This document defines the **destination**, not the path.
