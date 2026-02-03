"""Centralized scope enforcement."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import Principal, verify_api_key_detailed
from .database import Session
from .server_state import get_db

_security_scheme = HTTPBearer(auto_error=False)


def require_scopes(*scopes: str) -> Callable[[Request, Session], Principal]:
    required = set(scopes)

    def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_security_scheme),
        db: Session = Depends(get_db),
    ) -> Principal:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        principal = verify_api_key_detailed(db, credentials.credentials, required_scopes=required)
        request.state.principal = principal
        return principal

    return dependency
