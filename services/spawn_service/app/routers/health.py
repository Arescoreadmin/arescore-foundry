from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/live")
def live() -> dict:
    return {"status": "alive"}


@router.get("/ready")
def ready() -> dict:
    return {"status": "ready"}
