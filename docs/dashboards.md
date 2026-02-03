# Dashboard & Audit Packet Overview

## Tenant dashboards
- **Security Posture**: posture tiles, denial trends, and top deny drivers are available via tenant-scoped endpoints (`/ui/posture`, `/ui/decisions`). Each request requires tenant binding and UI scopes.
- **Evidence & Forensics**: chain-of-custody verification is surfaced via `/ui/forensics/chain/verify` with PASS/FAIL and first-bad-record reporting.
- **Controls & Remediation**: invariant proof matrix data is exposed via `/ui/controls` and `/ui/controls/{inv_id}` with evidence links and remediation guidance.

## Admin console
- **Tenant admin** and **global admin** dashboard paths return key, usage, quota, and audit log summaries.
- State-changing actions (key rotation and quota updates) emit structured audit events with request correlation IDs.

## Audit packet export
- The export endpoint (`POST /ui/audit/packet`) builds a deterministic evidence bundle containing:
  - `decisions.jsonl` (canonicalized decision list)
  - `chain_verification.json` (PASS/FAIL status + first bad record)
  - `manifest.json` (sha256 hashes and file sizes)
  - Optional `sbom.json` and `provenance.json` when present
- Bundles are stored in a temporary artifacts directory with TTL cleanup.
