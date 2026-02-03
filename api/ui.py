from __future__ import annotations

from pathlib import Path
from typing import Optional
import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, status

from api.security import (
    Principal,
    install_request_id_middleware,
    request_id_dependency,
    require_scopes,
    require_tenant,
)
from api.storage import DashboardStore, build_evidence_pack, build_posture, verify_chain


SCOPES = {
    "posture_read": "ui:posture:read",
    "decisions_read": "ui:decisions:read",
    "forensics_read": "ui:forensics:read",
    "controls_read": "ui:controls:read",
    "audit_export": "ui:audit:export",
}

DEFAULT_STORE = DashboardStore.demo()


def get_store() -> DashboardStore:
    return DEFAULT_STORE


app = FastAPI(title="Arescore UI API")
install_request_id_middleware(app)


def _paginate(limit: int, offset: int) -> dict:
    return {"limit": limit, "offset": offset}


@app.get("/ui/posture")
def posture_dashboard(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["posture_read"]])),
):
    tenant_decisions = [decision for decision in store.decisions if decision.tenant_id == principal.tenant_id]
    return {"request_id": request_id, "tenant_id": str(principal.tenant_id), "posture": build_posture(tenant_decisions)}


@app.get("/ui/decisions")
def list_decisions(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["decisions_read"]])),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    policy_filter: Optional[str] = Query(default=None, alias="policy"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    tenant_decisions = [decision for decision in store.decisions if decision.tenant_id == principal.tenant_id]
    if status_filter:
        tenant_decisions = [decision for decision in tenant_decisions if decision.status == status_filter]
    if policy_filter:
        tenant_decisions = [decision for decision in tenant_decisions if decision.policy == policy_filter]
    total = len(tenant_decisions)
    page = tenant_decisions[offset : offset + limit]
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "pagination": {"total": total, **_paginate(limit, offset)},
        "items": [
            {
                "id": decision.id,
                "created_at": decision.created_at.isoformat(),
                "status": decision.status,
                "policy": decision.policy,
                "reason": decision.reason,
                "actor": decision.actor,
                "metadata": decision.metadata,
            }
            for decision in page
        ],
    }


@app.get("/ui/decision/{decision_id}")
def get_decision(
    decision_id: str,
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["decisions_read"]])),
):
    for decision in store.decisions:
        if decision.id == decision_id and decision.tenant_id == principal.tenant_id:
            return {
                "request_id": request_id,
                "tenant_id": str(principal.tenant_id),
                "decision": {
                    "id": decision.id,
                    "created_at": decision.created_at.isoformat(),
                    "status": decision.status,
                    "policy": decision.policy,
                    "reason": decision.reason,
                    "actor": decision.actor,
                    "metadata": decision.metadata,
                },
            }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")


@app.get("/ui/forensics/chain/verify")
def verify_forensics_chain(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["forensics_read"]])),
):
    tenant_chain = [record for record in store.chain if record.tenant_id == principal.tenant_id]
    verified, first_bad = verify_chain(tenant_chain)
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "status": "PASS" if verified else "FAIL",
        "first_bad_record": first_bad.record_id if first_bad else None,
    }


@app.post("/ui/audit/packet")
def create_audit_packet(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["audit_export"]])),
):
    tenant_decisions = [decision for decision in store.decisions if decision.tenant_id == principal.tenant_id]
    tenant_chain = [record for record in store.chain if record.tenant_id == principal.tenant_id]
    base_dir = Path(os.getenv("UI_PACKETS_DIR", "artifacts/ui_packets"))
    pack = build_evidence_pack(
        tenant_id=principal.tenant_id,
        decisions=tenant_decisions,
        chain_records=tenant_chain,
        base_dir=base_dir,
    )
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "token": pack["token"],
        "path": pack["path"],
        "manifest": pack["manifest"],
        "chain_verification": pack["chain_verification"],
    }


@app.get("/ui/controls")
def list_controls(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["controls_read"]])),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    tenant_controls = [control for control in store.controls if control.tenant_id == principal.tenant_id]
    total = len(tenant_controls)
    page = tenant_controls[offset : offset + limit]
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "pagination": {"total": total, **_paginate(limit, offset)},
        "items": [
            {
                "id": control.id,
                "name": control.name,
                "status": control.status,
                "evidence_links": control.evidence_links,
                "remediation": control.remediation,
            }
            for control in page
        ],
    }


@app.get("/ui/controls/{inv_id}")
def get_control(
    inv_id: str,
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["controls_read"]])),
):
    for control in store.controls:
        if control.id == inv_id and control.tenant_id == principal.tenant_id:
            return {
                "request_id": request_id,
                "tenant_id": str(principal.tenant_id),
                "control": {
                    "id": control.id,
                    "name": control.name,
                    "status": control.status,
                    "evidence_links": control.evidence_links,
                    "remediation": control.remediation,
                },
            }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
