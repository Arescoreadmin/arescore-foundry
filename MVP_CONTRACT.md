# FROSTGATE FOUNDRY — MVP CONTRACT
## Non-Negotiable Scope

---

## 1. Definition of Done

MVP is complete when:

1. A tenant can call `/api/spawn` for track `netplus`
2. A real Docker-backed sandbox is created
3. Telemetry events are centrally collected
4. A session is scored with a winner
5. The dashboard shows:
   - battle running or stopped
   - wins and losses per side
6. Battles run continuously unless stopped
7. At midnight:
   - new battles stop
   - data is ingested
   - battles resume automatically
8. An AuditPack with a reproducible hash can be exported

Anything outside this list is **out of scope**.

---

## 2. Required Services (MVP Only)

| Service | Required Capability |
|------|---------------------|
| spawn_service | Auth, OPA gate, create session |
| orchestrator | Build and teardown containers |
| telemetry_collector | Accept and persist events |
| evidence_bundler | Export AuditPack |
| evaluator | Score and outcome |
| campaign_scheduler | Keep battles running |
| dashboard | Show status and stats |

---

## 3. Session Lifecycle


Lifecycle state is persisted and queryable.

---

## 4. Telemetry Event Schema (Authoritative)

```json
{
  "schema_version": 1,
  "session_id": "string",
  "actor": "orchestrator | reasoner | agent",
  "type": "state_change | decision | score",
  "payload": {},
  "ts": "ISO8601"
}

## 5. Audit Pack V.0

{
  "session_id": "string",
  "events": [],
  "score": {},
  "outcome": "core_win | spear_win | draw",
  "topology_ref": "string",
  "pack_hash": "sha256"
}

Serialization must be deterministic.

6. Campaign Control

Campaign fields:

enabled

desired_concurrency

Scheduler behavior:

fills to concurrency

stops spawning if disabled

Start/Stop via API

Midnight auto-pause via maintenance window

7. Dashboard (MVP UI)

Must show:

campaign status

active session count

wins and losses

Start / Stop buttons

last training run timestamp

No cinematic features.

8. Dev / Prod Rules

Development occurs in dev

Production is updated nightly only

Promotion happens during maintenance window

9. Explicitly Excluded

Live model retraining

Federation

Advanced topology overlays

Cinematic narration

Certification export

Universal Sandbox Connector

