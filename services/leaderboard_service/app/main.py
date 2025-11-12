"""FastAPI app managing learner leaderboard state."""

from __future__ import annotations

from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    learner_id: str
    score: float = Field(ge=0.0, le=100.0)
    difficulty: str
    notes: str = ""


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]


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

app = FastAPI(title="leaderboard_service")
_LEADERBOARD: Dict[str, LeaderboardEntry] = {}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
def ready() -> dict:
    return {"status": "ready"}


@app.post("/api/leaderboard")
def upsert(entry: LeaderboardEntry) -> LeaderboardEntry:
    if not entry.learner_id:
        raise HTTPException(status_code=400, detail="learner_id required")
    existing = _LEADERBOARD.get(entry.learner_id)
    if existing is None or entry.score >= existing.score:
        _LEADERBOARD[entry.learner_id] = entry
    return _LEADERBOARD[entry.learner_id]


@app.get("/api/leaderboard", response_model=LeaderboardResponse)
def top(limit: int = 10) -> LeaderboardResponse:
    sorted_entries = sorted(
        _LEADERBOARD.values(),
        key=lambda item: item.score,
        reverse=True,
    )
    return LeaderboardResponse(entries=sorted_entries[:limit])
