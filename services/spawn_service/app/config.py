from functools import lru_cache
from pydantic import BaseSettings, AnyUrl, Field
from typing import Optional


class Settings(BaseSettings):
    app_name: str = Field(default="Spawn Service", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")

    database_url: str = Field(
        default="postgresql+psycopg://spawn_service:spawn_service@localhost:5432/spawn_service",
        alias="DATABASE_URL",
    )

    orchestrator_url: AnyUrl | str = Field(
        default="http://orchestrator:8080", alias="ORCHESTRATOR_URL"
    )
    orchestrator_scenarios_path: str = Field(
        default="/api/scenarios", alias="ORCHESTRATOR_SCENARIOS_PATH"
    )

    console_base_url: str = Field(
        default="https://mvp.local/console", alias="CONSOLE_BASE_URL"
    )

    opa_url: Optional[AnyUrl | str] = Field(default="http://opa:8181", alias="OPA_URL")
    opa_policy_path: str = Field(default="/v1/data/spawn/allow", alias="OPA_POLICY_PATH")

    jwt_secret: Optional[str] = Field(default=None, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_audience: Optional[str] = Field(default=None, alias="JWT_AUDIENCE")
    jwt_issuer: Optional[str] = Field(default=None, alias="JWT_ISSUER")

    dev_bypass_token: str = Field(default="DEV-LOCAL-TOKEN", alias="DEV_BYPASS_TOKEN")
    demo_tenant_id: str = Field(
        default="00000000-0000-0000-0000-000000000001", alias="DEMO_TENANT_ID"
    )
    demo_plan_id: str = Field(
        default="00000000-0000-0000-0000-000000000010", alias="DEMO_PLAN_ID"
    )
    demo_template_id: str = Field(
        default="00000000-0000-0000-0000-000000000100", alias="DEMO_TEMPLATE_ID"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
