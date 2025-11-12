"""FastAPI app for computing aggregate performance scores."""

from __future__ import annotations

from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class PerformanceRequest(BaseModel):
    metrics: Dict[str, float] = Field(default_factory=dict)


class PerformanceResponse(BaseModel):
    score: float


from arescore_foundry_lib.logging_setup import configure_logging
configure_logging()

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from arescore_foundry_lib.logging_setup import _request_id_ctx, get_request_id
import logging, uuid
logger = logging.getLogger("request")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        _request_id_ctx.set(str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response

app = FastAPI(title="performance_evaluator")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    return {"status": "ready"}


@app.post("/api/score", response_model=PerformanceResponse)
def score(request: PerformanceRequest) -> PerformanceResponse:
    if not request.metrics:
        raise HTTPException(status_code=400, detail="metrics payload required")

    weights = {
        "accuracy": 0.6,
        "efficiency": 0.25,
        "safety": 0.15,
    }
    total_weight = 0.0
    aggregate = 0.0
    for key, value in request.metrics.items():
        weight = weights.get(key, 0.1)
        total_weight += weight
        aggregate += max(0.0, min(value, 1.0)) * weight

    score_value = min(100.0, max(0.0, (aggregate / total_weight) * 100 if total_weight else 0.0))
    return PerformanceResponse(score=score_value)
