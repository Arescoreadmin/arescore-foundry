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
