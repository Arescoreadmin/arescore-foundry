"""Simulation harness for smoke testing the reasoning workflow."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .reasoning import ReasoningEngine
from .schemas import ReasoningRequest, ReasoningResponse, ScenarioPlan
from .vector_store import MemoryRecord, TaskMemory


@dataclass
class SimulationOrchestrator:
    """In-memory orchestrator implementation for simulations."""

    scenarios: List[ScenarioPlan] = field(default_factory=list)

    async def create_scenario(self, plan: ScenarioPlan) -> str:
        self.scenarios.append(plan)
        return f"sim-{len(self.scenarios)}"


@dataclass
class SimulationPerformanceEvaluator:
    """Naive scoring using request metrics."""

    async def evaluate(self, metrics: Dict[str, float]) -> float:
        if not metrics:
            return 50.0
        weights = {
            "accuracy": 0.6,
            "efficiency": 0.3,
            "safety": 0.1,
        }
        score = 0.0
        for key, value in metrics.items():
            score += weights.get(key, 0.1) * value * 100
        return max(0.0, min(score, 100.0))


@dataclass
class SimulationDifficultyController:
    """Rules-based difficulty adjustment."""

    async def adjust(self, current: str, score: float) -> Dict[str, Any]:
        tiers = ["easy", "medium", "hard"]
        tier_index = tiers.index(current) if current in tiers else 1
        if score > 75 and tier_index < len(tiers) - 1:
            tier_index += 1
        elif score < 40 and tier_index > 0:
            tier_index -= 1
        difficulty = tiers[tier_index]
        recommendations = [
            f"Adjust assessment difficulty to {difficulty}",
            "Add targeted remediation exercise" if score < 60 else "Introduce stretch goal",
        ]
        return {"difficulty": difficulty, "recommendations": recommendations}


@dataclass
class SimulationLeaderboard:
    """Simple leaderboard collector."""

    entries: List[Dict[str, Any]] = field(default_factory=list)

    async def publish(self, learner_id: Optional[str], score: float, difficulty: str, notes: str) -> None:
        if learner_id is None:
            return
        self.entries.append(
            {
                "learner_id": learner_id,
                "score": score,
                "difficulty": difficulty,
                "notes": notes,
            }
        )


@dataclass
class SimulationOPA:
    """Always-allow OPA stub configurable for tests."""

    allowed: bool = True

    async def check(self, payload: Dict[str, Any]) -> bool:  # noqa: ARG002
        return self.allowed


@dataclass
class InMemoryTaskMemory(TaskMemory):
    """Task memory implementation used by the simulation harness."""

    records: List[MemoryRecord] = field(default_factory=list)

    async def retrieve(self, task_id: str, query: str, top_k: int = 3) -> List[MemoryRecord]:  # noqa: ARG002
        matches = [record for record in self.records if record.task_id == task_id]
        return matches[:top_k]

    async def store(self, record: MemoryRecord) -> None:
        self.records.append(record)


@dataclass
class SimulationHarness:
    """High-level helper to exercise the :class:`ReasoningEngine` end-to-end."""

    engine: ReasoningEngine

    @classmethod
    def build(cls) -> "SimulationHarness":
        task_memory = InMemoryTaskMemory()
        engine = ReasoningEngine(
            opa_client=SimulationOPA(),
            orchestrator_client=SimulationOrchestrator(),
            task_memory=task_memory,
            performance_client=SimulationPerformanceEvaluator(),
            difficulty_client=SimulationDifficultyController(),
            leaderboard_client=SimulationLeaderboard(),
        )
        return cls(engine=engine)

    async def run_once(
        self,
        *,
        task_id: str = "task-1",
        objective: str = "Improve network defense skills",
        learner_id: str = "learner-1",
    ) -> ReasoningResponse:
        request = ReasoningRequest(
            task_id=task_id,
            objective=objective,
            learner_id=learner_id,
            context={"difficulty": "medium", "template": "adaptive/defense.yaml"},
            performance_metrics={"accuracy": 0.72, "efficiency": 0.65},
            observations=["Learner struggled with lateral movement detection"],
        )
        return await self.engine.run_reasoning_cycle(request)


def run_blocking_simulation() -> ReasoningResponse:
    """Convenience wrapper for CLI-based smoke tests."""

    harness = SimulationHarness.build()
    return asyncio.run(harness.run_once())
