"""Initial spawn service schema"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from config import get_settings

# revision identifiers, used by Alembic.
revision = "20240528_0001"
down_revision = None
branch_labels = None
depends_on = None

settings = get_settings()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("max_concurrent_sessions", sa.Integer(), nullable=False, server_default=sa.text('5')),
        sa.Column("daily_spawn_limit", sa.Integer(), nullable=False, server_default=sa.text('20')),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=128), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False, server_default=sa.text('member')),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_email_tenant"),
    )

    op.create_table(
        "scenario_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("track", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_template_slug_tenant"),
    )

    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scenario_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenario_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("orchestrator_scenario_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text('spawning')),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    plans_table = sa.table(
        "plans",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("max_concurrent_sessions", sa.Integer()),
        sa.column("daily_spawn_limit", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    tenants_table = sa.table(
        "tenants",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("active", sa.Boolean()),
        sa.column("plan_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    templates_table = sa.table(
        "scenario_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("track", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("definition", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = _now()

    demo_plan_id = uuid.UUID(settings.demo_plan_id)
    demo_tenant_id = uuid.UUID(settings.demo_tenant_id)
    demo_template_id = uuid.UUID(settings.demo_template_id)

    op.bulk_insert(
        plans_table,
        [
            {
                "id": demo_plan_id,
                "name": "Demo",
                "description": "Default demonstration plan",
                "max_concurrent_sessions": 2,
                "daily_spawn_limit": 5,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    op.bulk_insert(
        tenants_table,
        [
            {
                "id": demo_tenant_id,
                "name": "demo",
                "slug": "demo",
                "active": True,
                "plan_id": demo_plan_id,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    op.bulk_insert(
        templates_table,
        [
            {
                "id": demo_template_id,
                "name": "Demo Net+",
                "slug": "demo-netplus",
                "track": "netplus",
                "description": "Sample scenario for demonstrations",
                "definition": {
                    "metadata": {"track": "netplus", "difficulty": "intro"},
                    "spec": {
                        "containers": [
                            {
                                "image": "arescore/netplus:latest",
                                "name": "student-workstation",
                                "resources": {"cpu": 1, "memory": "2Gi"},
                            }
                        ]
                    },
                },
                "tenant_id": demo_tenant_id,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("training_sessions")
    op.drop_table("scenario_templates")
    op.drop_table("users")
    op.drop_table("tenants")
    op.drop_table("plans")
