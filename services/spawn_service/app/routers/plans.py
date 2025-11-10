import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_principal
from ..database import get_db
from ..models import Plan
from ..schemas import PlanCreate, PlanRead, PlanUpdate, Principal

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead])
def list_plans(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[Plan]:
    plans = db.execute(select(Plan)).scalars().all()
    return plans


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_in: PlanCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Plan:
    if principal.tenant_id is not None:
        raise HTTPException(
            status_code=403, detail="Tenant-scoped token cannot create plans"
        )

    plan = Plan(**plan_in.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Plan:
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: uuid.UUID,
    plan_in: PlanUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Plan:
    if principal.tenant_id is not None:
        raise HTTPException(
            status_code=403, detail="Tenant-scoped token cannot update plans"
        )

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    for field, value in plan_in.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> None:
    if principal.tenant_id is not None:
        raise HTTPException(
            status_code=403, detail="Tenant-scoped token cannot delete plans"
        )

    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.delete(plan)
    db.commit()
