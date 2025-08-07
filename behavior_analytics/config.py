from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    orchestrator_url: str
    log_indexer_url: str
    auth_token: str
    anomaly_threshold: float = 0.9


@lru_cache
def get_settings() -> Settings:
    return Settings()
