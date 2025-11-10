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
