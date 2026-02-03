from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Iterable, Optional

from fastapi import Depends, Header, HTTPException, Request, status


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: Optional[uuid.UUID]
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


def _parse_scopes(raw_scopes: Optional[str]) -> frozenset[str]:
    if not raw_scopes:
        return frozenset()
    scopes = [scope.strip() for scope in raw_scopes.replace(",", " ").split()]
    return frozenset(filter(None, scopes))


async def get_principal(
    x_subject: Optional[str] = Header(default=None, alias="X-Subject"),
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
    x_scopes: Optional[str] = Header(default=None, alias="X-Scopes"),
) -> Principal:
    tenant_id: Optional[uuid.UUID] = None
    if x_tenant_id:
        try:
            tenant_id = uuid.UUID(x_tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tenant header") from exc
    return Principal(subject=x_subject or "anonymous", tenant_id=tenant_id, scopes=_parse_scopes(x_scopes))


def require_tenant(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant-scoped identity required")
    return principal


def require_scopes(required: Iterable[str]):
    required_set = tuple(required)

    def _check(principal: Principal = Depends(get_principal)) -> Principal:
        missing = [scope for scope in required_set if not principal.has_scope(scope)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope(s): {', '.join(missing)}",
            )
        return principal

    return _check


def require_csrf(request: Request, x_csrf_token: Optional[str] = Header(default=None, alias="X-CSRF-Token")) -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not x_csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")


async def request_id_dependency(request: Request) -> str:
    return request.state.request_id


def install_request_id_middleware(app) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
