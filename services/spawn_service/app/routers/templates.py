import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_current_principal
from ..database import get_db
from ..models import ScenarioTemplate, Tenant
from ..schemas import (
    Principal,
    ScenarioTemplateCreate,
    ScenarioTemplateRead,
    ScenarioTemplateUpdate,
)

router = APIRouter(prefix="/api/templates", tags=["scenario-templates"])


@router.get("", response_model=list[ScenarioTemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[ScenarioTemplate]:
    query = select(ScenarioTemplate)
    if principal.tenant_id:
        query = query.where(ScenarioTemplate.tenant_id == principal.tenant_id)
    templates = db.execute(query).scalars().all()
    return templates


@router.post("", response_model=ScenarioTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    template_in: ScenarioTemplateCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ScenarioTemplate:
    if principal.tenant_id and principal.tenant_id != template_in.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    tenant = db.get(Tenant, template_in.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    template = ScenarioTemplate(**template_in.model_dump())
    try:
        db.add(template)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Template slug already exists") from exc
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=ScenarioTemplateRead)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ScenarioTemplate:
    template = db.get(ScenarioTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if principal.tenant_id and principal.tenant_id != template.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return template


@router.put("/{template_id}", response_model=ScenarioTemplateRead)
def update_template(
    template_id: uuid.UUID,
    template_in: ScenarioTemplateUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ScenarioTemplate:
    template = db.get(ScenarioTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if principal.tenant_id and principal.tenant_id != template.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in template_in.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    try:
        db.add(template)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Template slug already exists") from exc

    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    template = db.get(ScenarioTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if principal.tenant_id and principal.tenant_id != template.tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(template)
    db.commit()
