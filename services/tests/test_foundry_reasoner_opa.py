import asyncio
from typing import Any, Dict, List

import pytest

from services.foundry_reasoner.app.reasoning import ReasoningDenied, ReasoningEngine
from services.foundry_reasoner.app.schemas import ReasoningRequest
from services.foundry_reasoner.app.vector_store import MemoryRecord, TaskMemory

@pytest.fixture
def anyio_backend() -> str:
    """Force AnyIO to use asyncio backend to avoid pulling in Trio."""

    return "asyncio"


class StubOPAClient:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.seen_inputs: List[Dict[str, Any]] = []

    async def check(self, payload: Dict[str, Any]) -> bool:
        self.seen_inputs.append(payload)
        await asyncio.sleep(0)
        return self.allowed


class StubTaskMemory(TaskMemory):
    def __init__(self, records: List[MemoryRecord] | None = None) -> None:
        self.records = records or []
        self.stored: List[MemoryRecord] = []

    async def retrieve(self, task_id: str, query: str, top_k: int = 3) -> List[MemoryRecord]:
        await asyncio.sleep(0)
        return [record for record in self.records if record.task_id == task_id][:top_k]

    async def store(self, record: MemoryRecord) -> None:
        await asyncio.sleep(0)
        self.stored.append(record)


class StubOrchestratorClient:
    def __init__(self) -> None:
        self.plans: List[Any] = []

    async def create_scenario(self, plan: Any) -> str:
        self.plans.append(plan)
        await asyncio.sleep(0)
        return "scenario-001"


class StubPerformanceClient:
    def __init__(self, score: float = 88.5) -> None:
        self.score = score
        self.requests: List[Dict[str, float]] = []

    async def evaluate(self, metrics: Dict[str, float]) -> float:
        self.requests.append(metrics)
        await asyncio.sleep(0)
        return self.score


class StubDifficultyClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    async def adjust(self, current: str, score: float) -> Dict[str, Any]:
        self.calls.append({"current": current, "score": score})
        await asyncio.sleep(0)
        return {
            "difficulty": "hard",
            "recommendations": ["Intensify scenario", "Add timed checkpoint"],
        }


class StubLeaderboardClient:
    def __init__(self) -> None:
        self.published: List[Dict[str, Any]] = []

    async def publish(self, learner_id: str | None, score: float, difficulty: str, notes: str) -> None:
        self.published.append(
            {
                "learner_id": learner_id,
                "score": score,
                "difficulty": difficulty,
                "notes": notes,
            }
        )
        await asyncio.sleep(0)


@pytest.mark.anyio("asyncio")
async def test_reasoning_cycle_requires_opa_allowance() -> None:
    opa_client = StubOPAClient(allowed=True)
    task_memory = StubTaskMemory(
        records=[
            MemoryRecord(
                task_id="task-1",
                content="Prior success: adaptive drill",
                vector=[0.1] * 64,
                metadata={"score": 72.0},
            )
        ]
    )
    engine = ReasoningEngine(
        opa_client=opa_client,
        orchestrator_client=StubOrchestratorClient(),
        task_memory=task_memory,
        performance_client=StubPerformanceClient(score=91.0),
        difficulty_client=StubDifficultyClient(),
        leaderboard_client=StubLeaderboardClient(),
    )

    request = ReasoningRequest(
        task_id="task-1",
        objective="Coach learner on defensive maneuvers",
        context={"difficulty": "medium", "template": "adaptive/defense.yaml"},
        learner_id="learner-1",
        performance_metrics={"accuracy": 0.82},
        observations=["Learner succeeded on previous drill"],
    )

    response = await engine.run_reasoning_cycle(request)

    assert response.allowed is True
    assert response.difficulty == "hard"
    assert response.recommendations == ["Intensify scenario", "Add timed checkpoint"]
    assert opa_client.seen_inputs == [
        {
            "task_id": "task-1",
            "learner_id": "learner-1",
            "objective": "Coach learner on defensive maneuvers",
            "context": {"difficulty": "medium", "template": "adaptive/defense.yaml"},
        }
    ]
    assert task_memory.stored, "memory persistence should be invoked"


@pytest.mark.anyio("asyncio")
async def test_reasoning_cycle_denied_when_opa_rejects() -> None:
    engine = ReasoningEngine(
        opa_client=StubOPAClient(allowed=False),
        orchestrator_client=StubOrchestratorClient(),
        task_memory=StubTaskMemory(),
        performance_client=StubPerformanceClient(),
        difficulty_client=StubDifficultyClient(),
        leaderboard_client=StubLeaderboardClient(),
    )

    request = ReasoningRequest(
        task_id="task-2",
        objective="Prepare learner for assessment",
        context={},
    )

    with pytest.raises(ReasoningDenied):
        await engine.run_reasoning_cycle(request)
