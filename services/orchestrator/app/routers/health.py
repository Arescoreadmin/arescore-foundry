# services/orchestrator/app/routers/health.py
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", include_in_schema=False)
async def root():
    return {"ok": True}


@router.get("/live", include_in_schema=False)
async def live():
    return {"ok": True}


@router.get("/ready", include_in_schema=False)
async def ready():
    # If you *later* want to add dependency checks (NATS, MinIO, OPA),
    # do it here but keep it fast and non-fatal for CI MVP.
    return {"ok": True}
