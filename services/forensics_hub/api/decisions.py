"""Decision persistence with evidence chain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .database import Session
from .forensics import CHAIN_ALG, DecisionPayload, GENESIS_HASH, compute_chain_hash


@dataclass(frozen=True)
class DecisionInput:
    tenant_id: str
    request_id: str
    decision: str
    policy_version: str
    inputs_fingerprint: str


@dataclass(frozen=True)
class DecisionRecord:
    id: int
    tenant_id: str
    request_id: str
    decision: str
    policy_version: str
    inputs_fingerprint: str
    created_at: datetime
    prev_hash: str
    chain_hash: str
    chain_alg: str
    chain_ts: datetime


def _previous_chain_hash(session: Session, tenant_id: str) -> str:
    row = session.conn.execute(
        """
        SELECT chain_hash
        FROM decisions
        WHERE tenant_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (tenant_id,),
    ).fetchone()
    return row["chain_hash"] if row else GENESIS_HASH


def persist_decision(
    session: Session,
    payload: DecisionInput,
    *,
    chain_ts: datetime | None = None,
) -> DecisionRecord:
    chain_ts = chain_ts or datetime.now(timezone.utc)
    prev_hash = _previous_chain_hash(session, payload.tenant_id)
    decision_payload = DecisionPayload(
        tenant_id=payload.tenant_id,
        request_id=payload.request_id,
        decision=payload.decision,
        policy_version=payload.policy_version,
        inputs_fingerprint=payload.inputs_fingerprint,
        chain_ts=chain_ts,
    )
    chain_hash = compute_chain_hash(prev_hash, decision_payload)
    created_at = datetime.now(timezone.utc)
    cursor = session.conn.execute(
        """
        INSERT INTO decisions (
            tenant_id, request_id, decision, policy_version, inputs_fingerprint,
            created_at, prev_hash, chain_hash, chain_alg, chain_ts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.tenant_id,
            payload.request_id,
            payload.decision,
            payload.policy_version,
            payload.inputs_fingerprint,
            created_at.isoformat(),
            prev_hash,
            chain_hash,
            CHAIN_ALG,
            chain_ts.isoformat(),
        ),
    )
    session.commit()
    record_id = cursor.lastrowid
    return DecisionRecord(
        id=record_id,
        tenant_id=payload.tenant_id,
        request_id=payload.request_id,
        decision=payload.decision,
        policy_version=payload.policy_version,
        inputs_fingerprint=payload.inputs_fingerprint,
        created_at=created_at,
        prev_hash=prev_hash,
        chain_hash=chain_hash,
        chain_alg=CHAIN_ALG,
        chain_ts=chain_ts,
    )
