"""FastAPI entry-point for the Foundry Reasoner service."""

from __future__ import annotations

import functools
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseSettings

from .clients import (
    DifficultyControllerClient,
    LeaderboardClient,
    OPAClient,
    OrchestratorClient,
    PerformanceEvaluatorClient,
)
from .reasoning import ReasoningDenied, ReasoningEngine
from .schemas import ReasoningRequest, ReasoningResponse
from .vector_store import QdrantTaskMemory


class Settings(BaseSettings):
    orchestrator_url: str = "http://orchestrator:8080"
    performance_evaluator_url: str = "http://performance_evaluator:8080"
    difficulty_controller_url: str = "http://difficulty_controller:8080"
    leaderboard_service_url: str = "http://leaderboard_service:8080"
    opa_url: str = "http://opa:8181/v1/data/foundry/reasoner/allow"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "task_memory"

    class Config:
        env_prefix = "FOUNDRY_REASONER_"
        case_sensitive = False


app = FastAPI(title="foundry_reasoner")
_task_memory: QdrantTaskMemory | None = None


@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_task_memory() -> QdrantTaskMemory:
    global _task_memory
    if _task_memory is None:
        settings = get_settings()
        _task_memory = QdrantTaskMemory(
            base_url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        )
    return _task_memory


def build_engine() -> ReasoningEngine:
    settings = get_settings()
    return ReasoningEngine(
        opa_client=OPAClient(settings.opa_url),
        orchestrator_client=OrchestratorClient(settings.orchestrator_url),
        task_memory=get_task_memory(),
        performance_client=PerformanceEvaluatorClient(settings.performance_evaluator_url),
        difficulty_client=DifficultyControllerClient(settings.difficulty_controller_url),
        leaderboard_client=LeaderboardClient(settings.leaderboard_service_url),
    )


async def get_engine() -> AsyncGenerator[ReasoningEngine, None]:
    yield build_engine()


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/live")
async def live() -> dict:
    return {"status": "alive"}


@app.get("/ready")
async def ready() -> dict:
    return {"status": "ready"}


@app.post("/api/reason", response_model=ReasoningResponse)
async def reason(
    request: ReasoningRequest, engine: ReasoningEngine = Depends(get_engine)
) -> ReasoningResponse:
    try:
        return await engine.run_reasoning_cycle(request)
    except ReasoningDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail=str(exc)) from exc
