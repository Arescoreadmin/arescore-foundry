"""Forensics Hub API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from .auth import Principal
from .auth_scopes import require_scopes
from .database import Session, create_db_engine, initialize_database
from .decisions import DecisionInput, persist_decision
from .forensics import verify_chain_for_tenant
from .server_state import configure_engine, get_db

CHAIN_VERIFY_SCOPE = "forensics:read"
DECISION_WRITE_SCOPE = "decisions:write"
DECISION_READ_SCOPE = "decisions:read"


class DecisionCreateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    request_id: str = Field(..., min_length=1)
    decision: str = Field(..., min_length=1)
    policy_version: str = Field(..., min_length=1)
    inputs_fingerprint: str = Field(..., min_length=1)
    chain_ts: datetime | None = None


class DecisionResponse(BaseModel):
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


def create_app(database_url: str | None = None) -> FastAPI:
    app = FastAPI(title="Forensics Hub")
    engine = create_db_engine(database_url)
    initialize_database(engine)
    configure_engine(engine)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"ok": "true"}

    @app.post("/api/decisions", response_model=DecisionResponse)
    def create_decision(
        payload: DecisionCreateRequest,
        principal: Principal = Depends(require_scopes(DECISION_WRITE_SCOPE)),
        db: Session = Depends(get_db),
    ) -> DecisionResponse:
        if principal.tenant_id and principal.tenant_id != payload.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if principal.tenant_id is None and "admin" not in principal.scopes:
            raise HTTPException(status_code=403, detail="Tenant-scoped key required")
        record = persist_decision(
            db,
            DecisionInput(
                tenant_id=payload.tenant_id,
                request_id=payload.request_id,
                decision=payload.decision,
                policy_version=payload.policy_version,
                inputs_fingerprint=payload.inputs_fingerprint,
            ),
            chain_ts=payload.chain_ts,
        )
        return DecisionResponse(**record.__dict__)

    @app.get("/api/decisions", response_model=list[DecisionResponse])
    def list_decisions(
        tenant_id: str = Query(..., min_length=1),
        verify_chain: bool = Query(default=False),
        principal: Principal = Depends(require_scopes(DECISION_READ_SCOPE)),
        db: Session = Depends(get_db),
    ) -> list[DecisionResponse]:
        if principal.tenant_id and principal.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if principal.tenant_id is None and "admin" not in principal.scopes:
            raise HTTPException(status_code=403, detail="Tenant-scoped key required")
        if verify_chain:
            result = verify_chain_for_tenant(db, tenant_id)
            if not result["ok"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result,
                )
        rows = db.conn.execute(
            """
            SELECT id, tenant_id, request_id, decision, policy_version, inputs_fingerprint,
                   created_at, prev_hash, chain_hash, chain_alg, chain_ts
            FROM decisions
            WHERE tenant_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (tenant_id,),
        ).fetchall()
        return [
            DecisionResponse(
                id=row["id"],
                tenant_id=row["tenant_id"],
                request_id=row["request_id"],
                decision=row["decision"],
                policy_version=row["policy_version"],
                inputs_fingerprint=row["inputs_fingerprint"],
                created_at=datetime.fromisoformat(row["created_at"]),
                prev_hash=row["prev_hash"],
                chain_hash=row["chain_hash"],
                chain_alg=row["chain_alg"],
                chain_ts=datetime.fromisoformat(row["chain_ts"]),
            )
            for row in rows
        ]

    @app.get("/forensics/chain/verify")
    def verify_chain(
        tenant_id: str = Query(..., min_length=1),
        limit: int | None = Query(default=None, ge=1),
        principal: Principal = Depends(require_scopes(CHAIN_VERIFY_SCOPE)),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        if principal.tenant_id and principal.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if principal.tenant_id is None and "admin" not in principal.scopes:
            raise HTTPException(status_code=403, detail="Tenant-scoped key required")
        return verify_chain_for_tenant(db, tenant_id, limit=limit)

    return app


app = create_app()
