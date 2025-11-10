import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_principal
from ..database import get_db
from ..models import Plan, Tenant
from ..schemas import Principal, TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantRead])
def list_tenants(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[Tenant]:
    query = select(Tenant)
    if principal.tenant_id:
        query = query.where(Tenant.id == principal.tenant_id)
    tenants = db.execute(query).scalars().all()
    return tenants


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_in: TenantCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    if principal.tenant_id is not None:
        raise HTTPException(
            status_code=403, detail="Tenant-scoped token cannot create tenants"
        )

    tenant = Tenant(**tenant_in.model_dump())
    try:
        db.add(tenant)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tenant with this name or slug exists") from exc
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantRead)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if principal.tenant_id and principal.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tenant


@router.put("/{tenant_id}", response_model=TenantRead)
def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: TenantUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if principal.tenant_id and principal.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in tenant_in.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    try:
        db.add(tenant)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate tenant name or slug") from exc

    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if principal.tenant_id and principal.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(tenant)
    db.commit()


@router.post("/{tenant_id}/plans/{plan_id}", response_model=TenantRead)
def assign_plan(
    tenant_id: uuid.UUID,
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if principal.tenant_id and principal.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    tenant.plan = plan
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant
