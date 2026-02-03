from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Optional


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class Decision:
    id: str
    tenant_id: uuid.UUID
    created_at: datetime
    status: str
    policy: str
    reason: str
    actor: str
    metadata: dict


@dataclass
class ChainRecord:
    record_id: str
    tenant_id: uuid.UUID
    sequence: int
    payload: dict
    prev_hash: str
    hash: str
    created_at: datetime


@dataclass
class ControlInvariant:
    id: str
    tenant_id: uuid.UUID
    name: str
    status: str
    remediation: str
    evidence_links: list[str]


@dataclass
class AuditEvent:
    event_id: str
    tenant_id: Optional[uuid.UUID]
    actor: str
    action: str
    created_at: datetime
    metadata: dict
    request_id: str


@dataclass
class DashboardStore:
    decisions: list[Decision] = field(default_factory=list)
    chain: list[ChainRecord] = field(default_factory=list)
    controls: list[ControlInvariant] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)

    @classmethod
    def demo(cls) -> "DashboardStore":
        tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        decisions = [
            Decision(
                id="dec-001",
                tenant_id=tenant_id,
                created_at=_now(),
                status="deny",
                policy="network-egress",
                reason="Blocked outbound to restricted ASN",
                actor="policy-engine",
                metadata={"severity": "high", "denies": 3},
            ),
            Decision(
                id="dec-002",
                tenant_id=tenant_id,
                created_at=_now(),
                status="allow",
                policy="device-attest",
                reason="Attestation verified",
                actor="attestor",
                metadata={"severity": "low", "denies": 0},
            ),
        ]
        chain = build_chain(
            tenant_id,
            [
                {"event": "decision", "id": "dec-001"},
                {"event": "decision", "id": "dec-002"},
            ],
        )
        controls = [
            ControlInvariant(
                id="inv-001",
                tenant_id=tenant_id,
                name="Zero-trust egress",
                status="at_risk",
                remediation="Rotate egress policy to least-privilege segments.",
                evidence_links=["/ui/decision/dec-001"],
            ),
            ControlInvariant(
                id="inv-002",
                tenant_id=tenant_id,
                name="Device attestation",
                status="healthy",
                remediation="Continue scheduled attestation audits.",
                evidence_links=["/ui/decision/dec-002"],
            ),
        ]
        return cls(decisions=decisions, chain=chain, controls=controls)


def build_chain(tenant_id: uuid.UUID, payloads: Iterable[dict]) -> list[ChainRecord]:
    chain: list[ChainRecord] = []
    prev_hash = "genesis"
    for idx, payload in enumerate(payloads, start=1):
        encoded = f"{prev_hash}:{_canonical_json(payload)}"
        digest = sha256(encoded.encode("utf-8")).hexdigest()
        chain.append(
            ChainRecord(
                record_id=f"rec-{idx:03d}",
                tenant_id=tenant_id,
                sequence=idx,
                payload=payload,
                prev_hash=prev_hash,
                hash=digest,
                created_at=_now(),
            )
        )
        prev_hash = digest
    return chain


def verify_chain(records: list[ChainRecord]) -> tuple[bool, Optional[ChainRecord]]:
    prev_hash = "genesis"
    for record in sorted(records, key=lambda item: item.sequence):
        encoded = f"{prev_hash}:{_canonical_json(record.payload)}"
        digest = sha256(encoded.encode("utf-8")).hexdigest()
        if record.prev_hash != prev_hash or record.hash != digest:
            return False, record
        prev_hash = record.hash
    return True, None


def build_posture(decisions: list[Decision]) -> dict:
    deny_count = sum(1 for decision in decisions if decision.status == "deny")
    allow_count = sum(1 for decision in decisions if decision.status == "allow")
    top_denies: dict[str, int] = {}
    for decision in decisions:
        if decision.status == "deny":
            top_denies[decision.reason] = top_denies.get(decision.reason, 0) + 1
    return {
        "tiles": {
            "allow": allow_count,
            "deny": deny_count,
            "total": len(decisions),
        },
        "trends": [
            {"label": "last_24h", "allow": allow_count, "deny": deny_count},
        ],
        "top_denies": sorted(top_denies.items(), key=lambda item: item[1], reverse=True)[:5],
    }


def _cleanup_dir(base_dir: Path, ttl_seconds: int) -> None:
    cutoff = time.time() - ttl_seconds
    for child in base_dir.glob("*"):
        if child.is_dir():
            try:
                if child.stat().st_mtime < cutoff:
                    for sub in child.rglob("*"):
                        if sub.is_file():
                            sub.unlink(missing_ok=True)
                    child.rmdir()
            except OSError:
                continue


def build_evidence_pack(
    *,
    tenant_id: uuid.UUID,
    decisions: list[Decision],
    chain_records: list[ChainRecord],
    base_dir: Path,
    ttl_seconds: int = 60 * 60 * 24,
) -> dict:
    base_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_dir(base_dir, ttl_seconds)

    verified, first_bad = verify_chain(chain_records)
    checked_at = (
        max((record.created_at for record in chain_records), default=_now())
        .astimezone(timezone.utc)
        .isoformat()
    )
    chain_payload = {
        "status": "PASS" if verified else "FAIL",
        "first_bad_record": first_bad.record_id if first_bad else None,
        "checked_at": checked_at,
    }
    ordered_decisions = sorted(decisions, key=lambda item: (item.created_at, item.id))
    decisions_jsonl = "\n".join(
        _canonical_json(
            {
                "id": decision.id,
                "tenant_id": str(decision.tenant_id),
                "created_at": decision.created_at.astimezone(timezone.utc).isoformat(),
                "status": decision.status,
                "policy": decision.policy,
                "reason": decision.reason,
                "actor": decision.actor,
                "metadata": decision.metadata,
            }
        )
        for decision in ordered_decisions
    ) + "\n"

    sbom_path = Path("artifacts/sbom.json")
    provenance_path = Path("artifacts/provenance.json")

    manifest_files: list[Path] = []
    bundle_root = base_dir / tenant_id.hex
    bundle_root.mkdir(parents=True, exist_ok=True)

    def write_file(rel_path: str, content: str) -> Path:
        path = bundle_root / rel_path
        path.write_text(content, encoding="utf-8")
        manifest_files.append(path)
        return path

    write_file("decisions.jsonl", decisions_jsonl)
    write_file("chain_verification.json", _canonical_json(chain_payload))

    if sbom_path.exists():
        write_file("sbom.json", sbom_path.read_text(encoding="utf-8"))
    if provenance_path.exists():
        write_file("provenance.json", provenance_path.read_text(encoding="utf-8"))

    manifest_entries = []
    for path in sorted(manifest_files, key=lambda item: item.name):
        payload = path.read_bytes()
        manifest_entries.append(
            {
                "file": path.name,
                "sha256": sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    manifest = {"algorithm": "sha256", "version": 1, "files": manifest_entries}
    manifest_payload = _canonical_json(manifest)
    manifest_path = bundle_root / "manifest.json"
    manifest_path.write_text(manifest_payload, encoding="utf-8")

    token = sha256(manifest_payload.encode("utf-8")).hexdigest()
    token_path = base_dir / token
    if token_path.exists():
        for sub in bundle_root.rglob("*"):
            if sub.is_file():
                sub.unlink(missing_ok=True)
        bundle_root.rmdir()
    else:
        bundle_root.rename(token_path)

    return {
        "token": token,
        "path": str(token_path),
        "manifest": manifest,
        "chain_verification": chain_payload,
    }
