import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_settings
from .schemas import Principal

security_scheme = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


def decode_token(token: str) -> Principal:
    settings = get_settings()

    if token == settings.dev_bypass_token:
        return Principal(
        subject="dev-local",
        tenant_id=uuid.UUID(settings.demo_tenant_id),
        scopes=["*"],
    )

    if not settings.jwt_secret:
        raise AuthError("JWT_SECRET is not configured")

    try:
        options = {"verify_aud": bool(settings.jwt_audience)}
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options=options,
        )
    except JWTError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc

    subject = payload.get("sub")
    if not subject:
        raise AuthError("Token missing 'sub' claim")

    tenant_claim = payload.get("tenant_id") or payload.get("https://arescore.io/tenant_id")
    tenant_id: Optional[uuid.UUID] = None
    if tenant_claim:
        try:
            tenant_id = uuid.UUID(str(tenant_claim))
        except ValueError as exc:
            raise AuthError("Invalid tenant_id in token") from exc

    scopes = payload.get("scope") or payload.get("scopes") or []
    if isinstance(scopes, str):
        scopes = scopes.split()

    return Principal(subject=subject, tenant_id=tenant_id, scopes=scopes)


async def get_current_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Principal:
    if credentials is None:
        raise AuthError("Authorization header missing")

    token = credentials.credentials
    principal = decode_token(token)
    return principal
