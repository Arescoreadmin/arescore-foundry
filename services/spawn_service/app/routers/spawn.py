import copy
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_principal
from ..config import get_settings
from ..database import get_db
from ..models import ScenarioTemplate, Tenant, TrainingSession, User
from ..opa import opa_client
from ..schemas import Principal, SpawnRequest, SpawnResponse

settings = get_settings()

router = APIRouter(prefix="/api", tags=["spawn"])


@router.post("/spawn", response_model=SpawnResponse)
async def spawn_scenario(
    request: SpawnRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> SpawnResponse:
    tenant_id = request.tenant_id or principal.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant must be specified")

    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")
    if not tenant.plan:
        raise HTTPException(status_code=400, detail="Tenant does not have an assigned plan")

    user: User | None = None
    if request.user_id:
        user = db.get(User, request.user_id)
        if not user or user.tenant_id != tenant.id:
            raise HTTPException(status_code=404, detail="User not found for tenant")

    template: ScenarioTemplate | None = None
    if request.scenario_template_id:
        template = db.get(ScenarioTemplate, request.scenario_template_id)
        if not template or template.tenant_id != tenant.id:
            raise HTTPException(status_code=404, detail="Scenario template not found")
    elif request.track:
        template = (
            db.execute(
                select(ScenarioTemplate).where(
                    ScenarioTemplate.tenant_id == tenant.id,
                    ScenarioTemplate.track == request.track,
                )
            )
            .scalars()
            .first()
        )
        if not template:
            raise HTTPException(status_code=404, detail="No template for requested track")
    else:
        raise HTTPException(
            status_code=400,
            detail="scenario_template_id or track must be provided",
        )

    active_sessions = db.scalar(
        select(func.count(TrainingSession.id)).where(
            TrainingSession.tenant_id == tenant.id,
            TrainingSession.status.in_(["spawning", "active"]),
        )
    ) or 0

    start_of_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    daily_spawns = db.scalar(
        select(func.count(TrainingSession.id)).where(
            TrainingSession.tenant_id == tenant.id,
            TrainingSession.created_at >= start_of_day,
        )
    ) or 0

    opa_payload = {
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
        },
        "plan": {
            "id": str(tenant.plan.id),
            "name": tenant.plan.name,
            "max_concurrent_sessions": tenant.plan.max_concurrent_sessions,
            "daily_spawn_limit": tenant.plan.daily_spawn_limit,
        },
        "usage": {
            "active_sessions": active_sessions,
            "daily_spawns": daily_spawns,
        },
        "request": {
            "scenario_template_id": str(template.id),
            "user_id": str(user.id) if user else None,
        },
    }

    await opa_client.authorize_spawn(opa_payload)

    session = TrainingSession(
        tenant_id=tenant.id,
        user_id=user.id if user else None,
        scenario_template_id=template.id,
    )
    db.add(session)
    db.flush()

    scenario_payload = copy.deepcopy(template.definition)
    metadata = scenario_payload.get("metadata") or {}
    metadata.setdefault("name", f"{template.slug}-{session.id}")
    scenario_payload["metadata"] = metadata

    url = f"{settings.orchestrator_url}{settings.orchestrator_scenarios_path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=scenario_payload)
    except httpx.RequestError as exc:
        session.status = "failed"
        db.add(session)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Orchestrator unreachable: {exc}") from exc

    if response.status_code not in {status.HTTP_200_OK, status.HTTP_201_CREATED}:
        session.status = "failed"
        db.add(session)
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Orchestrator error {response.status_code}: {response.text}",
        )

    payload = response.json() if response.content else {}
    orchestrator_id = (
        payload.get("id")
        or payload.get("scenario_id")
        or metadata.get("name")
        or str(session.id)
    )

    session.status = "active"
    session.started_at = datetime.now(timezone.utc)
    session.orchestrator_scenario_id = str(orchestrator_id)
    db.add(session)
    db.commit()
    db.refresh(session)

    access_url = f"{settings.console_base_url.rstrip('/')}/{session.orchestrator_scenario_id}"
    return SpawnResponse(
        scenario_id=session.orchestrator_scenario_id,
        access_url=access_url,
        training_session_id=session.id,
    )
