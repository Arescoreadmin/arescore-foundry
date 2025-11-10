"""Pydantic schemas for the Foundry Reasoner service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReasoningRequest(BaseModel):
    """Incoming request describing a reasoning task."""

    task_id: str = Field(..., description="Stable identifier for the task instance.")
    objective: str = Field(..., description="High level learning objective or mission.")
    context: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary contextual metadata.")
    learner_id: Optional[str] = Field(default=None, description="Learner identifier if available.")
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional raw metrics gathered from telemetry (accuracy, latency, etc.).",
    )
    observations: List[str] = Field(
        default_factory=list,
        description="Recent qualitative observations from sensors/coaches.",
    )


class MemoryRecordPayload(BaseModel):
    """Representation of a task memory record."""

    task_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReasoningResponse(BaseModel):
    """Response returned after completing a reasoning cycle."""

    allowed: bool = Field(..., description="Indicates whether OPA permitted the reasoning workflow.")
    scenario_id: Optional[str] = Field(
        default=None, description="Identifier returned by the orchestrator if an action was taken."
    )
    decision_summary: str = Field(..., description="Human-readable explanation of the decision.")
    score: float = Field(..., description="Normalized performance score.")
    difficulty: str = Field(..., description="Difficulty tier recommended for the next scenario.")
    recommendations: List[str] = Field(default_factory=list, description="Ordered list of concrete next steps.")
    memory_context: List[MemoryRecordPayload] = Field(
        default_factory=list,
        description="Top task-memory entries that influenced the decision.",
    )


class OPAEvaluationRequest(BaseModel):
    """Payload sent to OPA for gating reasoning requests."""

    input: Dict[str, Any]


class OPAEvaluationResponse(BaseModel):
    """Subset of the OPA decision response."""

    result: bool
    diagnostics: Optional[Dict[str, Any]] = None


class ScenarioPlan(BaseModel):
    """Representation of the scenario payload forwarded to the orchestrator."""

    name: str
    template: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    instructions: List[str] = Field(default_factory=list)
