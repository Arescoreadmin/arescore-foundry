from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_root() -> dict:
    return {"ok": True}

@router.get("/health/live")
async def health_live() -> dict:
    return {"ok": True, "status": "live"}

@router.get("/health/ready")
async def health_ready() -> dict:
    # If you want to add DB checks later, this is the place.
    return {"ok": True, "status": "ready"}
