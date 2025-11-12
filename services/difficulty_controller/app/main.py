"""FastAPI app for difficulty adjustments."""

from __future__ import annotations

from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field


def _bounded(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(value, upper))


class DifficultyRequest(BaseModel):
    current_difficulty: str = Field(default="medium")
    score: float = Field(default=50.0, ge=0.0, le=100.0)


class DifficultyResponse(BaseModel):
    difficulty: str
    recommendations: List[str]


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

app = FastAPI(title="difficulty_controller")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    return {"status": "ready"}


@app.post("/api/difficulty", response_model=DifficultyResponse)
def difficulty(request: DifficultyRequest) -> DifficultyResponse:
    tiers = ["easy", "medium", "hard"]
    index = tiers.index(request.current_difficulty) if request.current_difficulty in tiers else 1

    score = _bounded(request.score)
    if score > 75 and index < len(tiers) - 1:
        index += 1
    elif score < 45 and index > 0:
        index -= 1

    new_difficulty = tiers[index]
    recommendations = [
        f"Set next scenario difficulty to {new_difficulty}",
        "Schedule guided remediation" if score < 60 else "Introduce enrichment objective",
    ]
    return DifficultyResponse(difficulty=new_difficulty, recommendations=recommendations)
