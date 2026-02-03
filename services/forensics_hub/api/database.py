"""Database helpers for the forensics hub."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

DEFAULT_DATABASE_URL = "sqlite:///./forensics_hub.db"


@dataclass(frozen=True)
class Engine:
    """Represents the SQLite database location."""

    path: Path


def _normalise_database_url(database_url: str | None) -> Path:
    url = database_url or DEFAULT_DATABASE_URL
    parsed = urlparse(url)
    if parsed.scheme != "sqlite":  # pragma: no cover - defensive
        raise ValueError("Only sqlite URLs are supported in this environment")

    path = parsed.path or ""
    if path.startswith("//"):
        path = path[1:]
    else:
        path = path.lstrip("/")
    if not path and parsed.netloc:
        path = parsed.netloc
    return Path(path or "forensics_hub.db")


def create_db_engine(database_url: str | None = None) -> Engine:
    db_path = _normalise_database_url(database_url)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Engine(path=db_path)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: Iterable[str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column_def in columns:
        column_name = column_def.split()[0]
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def initialize_database(engine: Engine) -> None:
    with sqlite3.connect(engine.path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                scopes TEXT NOT NULL,
                hashed_key TEXT NOT NULL,
                hash_alg TEXT NOT NULL,
                hash_params TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                inputs_fingerprint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                prev_hash TEXT,
                chain_hash TEXT NOT NULL,
                chain_alg TEXT NOT NULL,
                chain_ts TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_tenant_created
            ON decisions (tenant_id, created_at, id);
            """
        )

        _ensure_columns(
            conn,
            "decisions",
            [
                "prev_hash TEXT",
                "chain_hash TEXT NOT NULL DEFAULT ''",
                "chain_alg TEXT NOT NULL DEFAULT ''",
                "chain_ts TEXT NOT NULL DEFAULT ''",
            ],
        )
        _ensure_columns(
            conn,
            "api_keys",
            [
                "hash_alg TEXT NOT NULL DEFAULT ''",
                "hash_params TEXT NOT NULL DEFAULT '{}'",
                "tenant_id TEXT",
                "scopes TEXT NOT NULL DEFAULT ''",
            ],
        )
        conn.commit()


class Session:
    """Lightweight SQLite session wrapper."""

    def __init__(self, engine: Engine):
        self._conn = sqlite3.connect(str(engine.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:  # pragma: no cover - defensive
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()
