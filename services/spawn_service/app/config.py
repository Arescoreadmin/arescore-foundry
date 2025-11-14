from typing import Optional, Union
import logging

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Pydantic v2-style config
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Spawn Service"
    app_version: str = "0.1.0"

    # DB
    database_url: str = Field(
        default="sqlite:///./spawn_service.db",
        alias="DATABASE_URL",
    )

    # Service URLs
    log_indexer_url: str = Field(
        default="http://log_indexer:9000",
        alias="LOG_INDEXER_URL",
    )
    frostgatecore_url: str = Field(
        default="http://frostgatecore:8001",
        alias="FROSTGATECORE_URL",
    )
    sentinelred_url: str = Field(
        default="http://sentinelred:8002",
        alias="SENTINELRED_URL",
    )
    mutation_engine_url: str = Field(
        default="http://mutation_engine:8003",
        alias="MUTATION_ENGINE_URL",
    )
    behavior_analytics_url: str = Field(
        default="http://behavior_analytics:8004",
        alias="BEHAVIOR_ANALYTICS_URL",
    )
    vite_api_base: str = Field(
        default="http://localhost:8000",
        alias="VITE_API_BASE",
    )

    # Tokens
    log_token: str = Field(
        default="dev",
        alias="LOG_TOKEN",
    )
    orch_token: str = Field(
        default="dev",
        alias="ORCH_TOKEN",
    )

    # OPA bits
    opa_url: Optional[Union[AnyUrl, str]] = Field(
        default="http://opa:8181",
        alias="OPA_URL",
    )

    # THIS is the field that was missing and caused the crash
    opa_policy_path: str = Field(
        default="spawn/opa/policy",
        alias="OPA_POLICY_PATH",
    )

    jwt_secret: Optional[str] = Field(
        default=None,
        alias="JWT_SECRET",
    )


def get_settings() -> Settings:
    settings = Settings()
    # Don’t log secrets
    safe = settings.model_dump(exclude={"jwt_secret"})
    logger.debug("Spawn Settings loaded: %s", safe)
    return settings

