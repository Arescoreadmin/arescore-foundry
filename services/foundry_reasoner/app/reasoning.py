"""Reasoning workflow orchestrator."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .clients import (
    DifficultyControllerClient,
    LeaderboardClient,
    OPAClient,
    OrchestratorClient,
    PerformanceEvaluatorClient,
)
from .embedding import embed_text
from .schemas import MemoryRecordPayload, ReasoningRequest, ReasoningResponse, ScenarioPlan
from .vector_store import MemoryRecord, TaskMemory


class ReasoningDenied(Exception):
    """Raised when OPA denies a reasoning attempt."""


class ReasoningEngine:
    """Encapsulates the multi-step reasoning workflow."""

    def __init__(
        self,
        *,
        opa_client: OPAClient,
        orchestrator_client: OrchestratorClient,
        task_memory: TaskMemory,
        performance_client: PerformanceEvaluatorClient,
        difficulty_client: DifficultyControllerClient,
        leaderboard_client: LeaderboardClient,
    ) -> None:
        self.opa_client = opa_client
        self.orchestrator_client = orchestrator_client
        self.task_memory = task_memory
        self.performance_client = performance_client
        self.difficulty_client = difficulty_client
        self.leaderboard_client = leaderboard_client

    async def run_reasoning_cycle(self, request: ReasoningRequest) -> ReasoningResponse:
        """Execute the end-to-end reasoning workflow."""

        opa_allowed = await self.opa_client.check(
            {
                "task_id": request.task_id,
                "learner_id": request.learner_id,
                "objective": request.objective,
                "context": request.context,
            }
        )
        if not opa_allowed:
            raise ReasoningDenied("OPA denied reasoning request")

        memory_records = await self.task_memory.retrieve(
            request.task_id, request.objective or "generic"
        )
        memory_payloads = [
            MemoryRecordPayload(
                task_id=record.task_id,
                content=record.content,
                score=record.metadata.get("score", 0.0),
                metadata={k: v for k, v in record.metadata.items() if k != "score"},
            )
            for record in memory_records
        ]

        plan = self._build_plan(request, memory_payloads)
        scenario_id = await self.orchestrator_client.create_scenario(plan)

        score = await self.performance_client.evaluate(request.performance_metrics)
        difficulty_data = await self.difficulty_client.adjust(
            current=request.context.get("difficulty", "medium"), score=score
        )
        difficulty = str(difficulty_data.get("difficulty", "medium"))
        recommendations = difficulty_data.get("recommendations") or []

        await self.leaderboard_client.publish(
            request.learner_id,
            score,
            difficulty,
            notes=f"Scenario {scenario_id} executed on {dt.datetime.now(dt.timezone.utc).isoformat()}",
        )

        await self._persist_memory(
            request=request,
            scenario_id=scenario_id,
            score=score,
            difficulty=difficulty,
            recommendations=recommendations,
        )

        decision_summary = self._summarise_decision(plan, score, difficulty)

        return ReasoningResponse(
            allowed=True,
            scenario_id=scenario_id,
            decision_summary=decision_summary,
            score=score,
            difficulty=difficulty,
            recommendations=recommendations,
            memory_context=memory_payloads,
        )

    def _build_plan(
        self, request: ReasoningRequest, memory: List[MemoryRecordPayload]
    ) -> ScenarioPlan:
        instructions: List[str] = []
        if memory:
            instructions.append("Leverage prior successes:")
            instructions.extend(f"- {item.content}" for item in memory)
        if request.observations:
            instructions.append("Recent observations:")
            instructions.extend(f"- {obs}" for obs in request.observations)
        instructions.append(f"Objective: {request.objective}")
        return ScenarioPlan(
            name=f"reasoner-{request.task_id}",
            template=request.context.get("template", "adaptive/default.yaml"),
            metadata={
                "task_id": request.task_id,
                "learner_id": request.learner_id,
                "difficulty": request.context.get("difficulty", "medium"),
            },
            instructions=instructions,
        )

    async def _persist_memory(
        self,
        *,
        request: ReasoningRequest,
        scenario_id: Optional[str],
        score: float,
        difficulty: str,
        recommendations: List[str],
    ) -> None:
        metadata: Dict[str, Any] = {
            "scenario_id": scenario_id,
            "score": score,
            "difficulty": difficulty,
            "recommendations": recommendations,
        }
        vector = embed_text(
            f"{request.objective} {' '.join(request.observations)}".strip()
        )
        record = MemoryRecord(
            task_id=request.task_id,
            content=f"Objective '{request.objective}' executed with score {score:.1f}",
            vector=vector,
            metadata=metadata,
        )
        await self.task_memory.store(record)

    def _summarise_decision(
        self, plan: ScenarioPlan, score: float, difficulty: str
    ) -> str:
        return (
            f"Submitted plan '{plan.name}' using template {plan.template}. "
            f"Score {score:.1f} led to difficulty '{difficulty}'."
        )
