"""Database helpers for ingestor services."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = os.getenv("FOUNDRY_DATABASE_URL", "sqlite:///./foundry_ingestor.db")


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create an SQLAlchemy engine for the given database URL."""

    return create_engine(database_url or DEFAULT_DATABASE_URL, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured session factory."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
