import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    max_concurrent_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    daily_spawn_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    tenants: Mapped[list["Tenant"]] = relationship(
        "Tenant", back_populates="plan"
    )


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )

    plan: Mapped[Plan | None] = relationship("Plan", back_populates="tenants")
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="tenant", cascade="all,delete", passive_deletes=True
    )
    sessions: Mapped[list["TrainingSession"]] = relationship(
        "TrainingSession",
        back_populates="tenant",
        cascade="all,delete",
        passive_deletes=True,
    )
    scenario_templates: Mapped[list["ScenarioTemplate"]] = relationship(
        "ScenarioTemplate",
        back_populates="tenant",
        cascade="all,delete",
        passive_deletes=True,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_email_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="member")
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="users")
    sessions: Mapped[list["TrainingSession"]] = relationship(
        "TrainingSession", back_populates="user", passive_deletes=True
    )


class ScenarioTemplate(Base, TimestampMixin):
    __tablename__ = "scenario_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_template_slug_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    track: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="scenario_templates")
    sessions: Mapped[list["TrainingSession"]] = relationship(
        "TrainingSession", back_populates="scenario_template", passive_deletes=True
    )


class TrainingSession(Base, TimestampMixin):
    __tablename__ = "training_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    scenario_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenario_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    orchestrator_scenario_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="spawning")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="sessions")
    user: Mapped[User | None] = relationship("User", back_populates="sessions")
    scenario_template: Mapped[ScenarioTemplate | None] = relationship(
        "ScenarioTemplate", back_populates="sessions"
    )
