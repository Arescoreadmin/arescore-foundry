import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    max_concurrent_sessions: int = Field(ge=0)
    daily_spawn_limit: int = Field(ge=0)


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_concurrent_sessions: Optional[int] = Field(default=None, ge=0)
    daily_spawn_limit: Optional[int] = Field(default=None, ge=0)


class PlanRead(PlanBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantBase(BaseModel):
    name: str
    slug: str
    active: bool = True
    plan_id: Optional[uuid.UUID] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    active: Optional[bool] = None
    plan_id: Optional[uuid.UUID] = None


class TenantRead(TenantBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str = "member"


class UserCreate(UserBase):
    tenant_id: uuid.UUID


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


class UserRead(UserBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioTemplateBase(BaseModel):
    name: str
    slug: str
    track: str
    description: Optional[str] = None
    definition: dict


class ScenarioTemplateCreate(ScenarioTemplateBase):
    tenant_id: uuid.UUID


class ScenarioTemplateUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    track: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[dict] = None


class ScenarioTemplateRead(ScenarioTemplateBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpawnRequest(BaseModel):
    tenant_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    scenario_template_id: Optional[uuid.UUID] = None
    track: Optional[str] = None


class SpawnResponse(BaseModel):
    scenario_id: str
    access_url: Optional[str] = None
    training_session_id: uuid.UUID


class HealthResponse(BaseModel):
    ok: bool = True


class Principal(BaseModel):
    subject: str
    tenant_id: Optional[uuid.UUID]
    scopes: list[str] = []
