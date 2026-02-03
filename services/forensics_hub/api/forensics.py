"""Evidence chain helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .database import Session

CHAIN_ALG = "sha256/canonical-json/v1"
GENESIS_HASH = "GENESIS"


@dataclass(frozen=True)
class DecisionPayload:
    tenant_id: str
    request_id: str
    decision: str
    policy_version: str
    inputs_fingerprint: str
    chain_ts: datetime

    def canonical(self) -> str:
        payload: dict[str, Any] = {
            "chain_ts": self.chain_ts.astimezone(timezone.utc).isoformat(),
            "decision": self.decision,
            "inputs_fingerprint": self.inputs_fingerprint,
            "policy_version": self.policy_version,
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
        }
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_chain_hash(prev_hash: str, payload: DecisionPayload) -> str:
    canonical_payload = payload.canonical()
    payload_hash = _sha256_hex(canonical_payload)
    return _sha256_hex(f"{prev_hash}:{payload_hash}")


def verify_chain_for_tenant(
    session: Session,
    tenant_id: str,
    limit: int | None = None,
) -> dict[str, Any]:
    query = """
        SELECT id, tenant_id, request_id, decision, policy_version, inputs_fingerprint,
               created_at, prev_hash, chain_hash, chain_alg, chain_ts
        FROM decisions
        WHERE tenant_id = ?
        ORDER BY created_at ASC, id ASC
    """
    params: tuple[Any, ...] = (tenant_id,)
    if limit is not None:
        query += " LIMIT ?"
        params = (tenant_id, limit)

    rows = session.conn.execute(query, params).fetchall()
    expected_prev = GENESIS_HASH
    checked = 0
    for row in rows:
        checked += 1
        if row["prev_hash"] != expected_prev:
            return {
                "ok": False,
                "first_bad_id": row["id"],
                "reason": "prev_hash mismatch",
                "checked": checked,
            }

        chain_ts = datetime.fromisoformat(row["chain_ts"])
        payload = DecisionPayload(
            tenant_id=row["tenant_id"],
            request_id=row["request_id"],
            decision=row["decision"],
            policy_version=row["policy_version"],
            inputs_fingerprint=row["inputs_fingerprint"],
            chain_ts=chain_ts,
        )
        computed_hash = compute_chain_hash(expected_prev, payload)
        if row["chain_hash"] != computed_hash:
            return {
                "ok": False,
                "first_bad_id": row["id"],
                "reason": "chain_hash mismatch",
                "checked": checked,
            }
        if row["chain_alg"] != CHAIN_ALG:
            return {
                "ok": False,
                "first_bad_id": row["id"],
                "reason": "chain_alg mismatch",
                "checked": checked,
            }
        expected_prev = computed_hash

    return {"ok": True, "first_bad_id": None, "reason": None, "checked": checked}
