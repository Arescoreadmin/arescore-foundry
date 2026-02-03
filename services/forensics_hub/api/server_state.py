"""Application state helpers."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import HTTPException, status

from .database import Engine, Session

_engine: Engine | None = None


def configure_engine(engine: Engine) -> None:
    global _engine
    _engine = engine


def get_db() -> Iterator[Session]:
    if _engine is None:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DB not configured")
    session = Session(_engine)
    try:
        yield session
    finally:
        session.close()
