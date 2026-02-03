from __future__ import annotations

from typing import Optional
import uuid

from fastapi import Depends, FastAPI, Query

from api.security import (
    Principal,
    install_request_id_middleware,
    request_id_dependency,
    require_csrf,
    require_scopes,
    require_tenant,
)
from api.storage import AuditEvent, DashboardStore, _now


SCOPES = {
    "tenant_admin": "admin:tenant",
    "global_admin": "admin:global",
    "audit_read": "admin:audit:read",
    "keys_write": "admin:keys:write",
    "quota_write": "admin:quota:write",
}

DEFAULT_STORE = DashboardStore.demo()


def get_store() -> DashboardStore:
    return DEFAULT_STORE


app = FastAPI(title="Arescore Admin Gateway")
install_request_id_middleware(app)


def _paginate(limit: int, offset: int) -> dict:
    return {"limit": limit, "offset": offset}


def _log_audit_event(
    *,
    store: DashboardStore,
    tenant_id: Optional[uuid.UUID],
    actor: str,
    action: str,
    request_id: str,
    metadata: Optional[dict] = None,
) -> AuditEvent:
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        created_at=_now(),
        metadata=metadata or {},
        request_id=request_id,
    )
    store.audit_events.append(event)
    return event


@app.get("/admin/console/tenant")
def tenant_console(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["tenant_admin"]])),
):
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "keys": [{"id": "key-01", "status": "active", "last_rotated": "2024-08-01"}],
        "usage": {"sessions": 12, "quota": "80%"},
    }


@app.get("/admin/console/global")
def global_console(
    principal: Principal = Depends(require_scopes([SCOPES["global_admin"]])),
    request_id: str = Depends(request_id_dependency),
):
    return {
        "request_id": request_id,
        "tenant_count": 14,
        "regions": ["us-east", "eu-central"],
    }


@app.get("/admin/console/audit-log")
def list_audit_events(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["audit_read"]])),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    tenant_events = [event for event in store.audit_events if event.tenant_id == principal.tenant_id]
    total = len(tenant_events)
    page = tenant_events[offset : offset + limit]
    return {
        "request_id": request_id,
        "tenant_id": str(principal.tenant_id),
        "pagination": {"total": total, **_paginate(limit, offset)},
        "items": [
            {
                "event_id": event.event_id,
                "action": event.action,
                "actor": event.actor,
                "created_at": event.created_at.isoformat(),
                "metadata": event.metadata,
                "request_id": event.request_id,
            }
            for event in page
        ],
    }


@app.post("/admin/console/keys/rotate", dependencies=[Depends(require_csrf)])
def rotate_keys(
    principal: Principal = Depends(require_tenant),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
    _: Principal = Depends(require_scopes([SCOPES["keys_write"]])),
):
    event = _log_audit_event(
        store=store,
        tenant_id=principal.tenant_id,
        actor=principal.subject,
        action="rotate_keys",
        request_id=request_id,
    )
    return {"request_id": request_id, "status": "ok", "event_id": event.event_id}


@app.post("/admin/console/tenants/{tenant_id}/quota", dependencies=[Depends(require_csrf)])
def update_quota(
    tenant_id: uuid.UUID,
    principal: Principal = Depends(require_scopes([SCOPES["global_admin"], SCOPES["quota_write"]])),
    store: DashboardStore = Depends(get_store),
    request_id: str = Depends(request_id_dependency),
):
    event = _log_audit_event(
        store=store,
        tenant_id=tenant_id,
        actor=principal.subject,
        action="update_quota",
        request_id=request_id,
        metadata={"tenant_id": str(tenant_id)},
    )
    return {"request_id": request_id, "status": "ok", "event_id": event.event_id}
