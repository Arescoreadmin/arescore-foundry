"""API routes for the orchestrator."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .schemas import Topology
from .services import SessionService
from .state import SessionRecord, SessionState


class TemplateValidationRequest(BaseModel):
    topology: str


class TemplateValidationResponse(BaseModel):
    name: str
    containers: int
    networks: int
    links: int


class SessionCreateRequest(BaseModel):
    name: str
    topology: str


class SessionResponse(BaseModel):
    id: str
    name: str
    state: SessionState
    plan: Dict[str, Any] | None = None

    @classmethod
    def from_record(cls, record: SessionRecord, *, include_plan: bool = False) -> "SessionResponse":
        payload: Dict[str, Any] | None = None
        if include_plan:
            payload = record.topology.model_dump()
        return cls(id=record.id, name=record.name, state=record.state, plan=payload)


class SessionStateUpdateRequest(BaseModel):
    state: SessionState
    detail: str | None = None


def build_admin_router(*, service: SessionService) -> APIRouter:
    router = APIRouter()

    @router.post("/templates/validate", response_model=TemplateValidationResponse)
    async def validate_template(payload: TemplateValidationRequest) -> TemplateValidationResponse:
        topology = Topology.from_yaml(payload.topology)
        return TemplateValidationResponse(
            name=topology.name,
            containers=len(topology.containers),
            networks=len(topology.networks),
            links=len(topology.links),
        )

    @router.post("/sessions", response_model=SessionResponse)
    async def create_session(payload: SessionCreateRequest) -> SessionResponse:
        topology = Topology.from_yaml(payload.topology)
        record, plan = await service.create_session(name=payload.name, topology=topology)
        return SessionResponse(id=record.id, name=record.name, state=record.state, plan=plan.model_dump())

    @router.get("/sessions", response_model=list[SessionResponse])
    async def list_sessions() -> list[SessionResponse]:
        return [SessionResponse.from_record(record) for record in service.list_sessions()]

    @router.get("/sessions/{session_id}", response_model=SessionResponse)
    async def get_session(session_id: str) -> SessionResponse:
        try:
            record = service.get_session(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return SessionResponse.from_record(record, include_plan=True)

    @router.post("/sessions/{session_id}/state")
    async def update_session_state(session_id: str, payload: SessionStateUpdateRequest) -> SessionResponse:
        await service.publish_status(session_id, payload.state, payload.detail)
        record = service.get_session(session_id)
        return SessionResponse.from_record(record)

    return router


__all__ = ["build_admin_router"]
