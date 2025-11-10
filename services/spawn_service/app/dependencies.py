from fastapi import Depends, HTTPException, status
from .auth import get_current_principal
from .schemas import Principal


def require_tenant(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant-scoped token required",
        )
    return principal
