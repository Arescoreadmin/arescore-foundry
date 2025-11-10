"""SQLite-backed storage helpers for ingestor services."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Type, TypeVar
from urllib.parse import urlparse

from .models import Device, NetworkSegment, Site, Snapshot
from .query import Result, SelectQuery

T = TypeVar("T")

DEFAULT_DATABASE_URL = "sqlite:///./foundry_ingestor.db"


@dataclass(frozen=True)
class Engine:
    """Representation of a SQLite database location."""

    path: Path


def _normalise_database_url(database_url: str | None) -> Path:
    url = database_url or DEFAULT_DATABASE_URL
    parsed = urlparse(url)
    if parsed.scheme != "sqlite":  # pragma: no cover - defensive
        raise ValueError("Only sqlite URLs are supported in the kata environment")

    path = parsed.path or ""
    if path.startswith("//"):
        path = path[1:]
    else:
        path = path.lstrip("/")
    if not path and parsed.netloc:
        path = parsed.netloc
    return Path(path or "foundry_ingestor.db")


def create_db_engine(database_url: str | None = None) -> Engine:
    """Create an engine describing where the SQLite file lives."""

    db_path = _normalise_database_url(database_url)
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Engine(path=db_path)


def initialize_database(engine: Engine) -> None:
    """Create tables if they do not already exist."""

    with sqlite3.connect(engine.path) as connection:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS sites (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS network_segments (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                cidr TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(site_id, code),
                FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                site_id TEXT NOT NULL,
                segment_id TEXT,
                code TEXT NOT NULL,
                hostname TEXT NOT NULL,
                ip_address TEXT,
                device_type TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(site_id, code),
                FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE,
                FOREIGN KEY(segment_id) REFERENCES network_segments(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id TEXT PRIMARY KEY,
                external_id TEXT NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                version INTEGER NOT NULL,
                site_id TEXT,
                collected_at TEXT,
                ingested_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                UNIQUE(source, external_id),
                FOREIGN KEY(site_id) REFERENCES sites(id)
            );
            """
        )
        connection.commit()


class SessionFactory:
    """Callable factory that produces :class:`Session` instances."""

    def __init__(self, engine: Engine):
        self._engine = engine

    def __call__(self) -> "Session":
        return Session(self._engine)


def create_session_factory(engine: Engine) -> SessionFactory:
    return SessionFactory(engine)


class Session:
    """Minimal session wrapper around sqlite3."""

    def __init__(self, engine: Engine):
        self._conn = sqlite3.connect(str(engine.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def __enter__(self) -> "Session":  # pragma: no cover - exercised indirectly
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - defensive
        self.close()

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:  # pragma: no cover - defensive
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def execute(self, query: SelectQuery[T]) -> Result[T]:
        table = query.model.table_name
        rows = self._conn.execute(f"SELECT * FROM {table}").fetchall()
        objects = [self._deserialize(query.model, row) for row in rows]
        return Result(objects)

    # CRUD helpers used by the ingestion logic --------------------------------
    def get_site_by_code(self, code: str) -> Site | None:
        row = self._conn.execute("SELECT * FROM sites WHERE code = ?", (code,)).fetchone()
        return self._deserialize(Site, row) if row else None

    def create_site(self, payload: dict[str, Any]) -> Site:
        site = Site(
            code=payload["code"],
            name=payload["name"],
            description=payload.get("description"),
            metadata_=payload.get("metadata", {}),
        )
        self._conn.execute(
            """
            INSERT INTO sites (id, code, name, description, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site.id,
                site.code,
                site.name,
                site.description,
                json.dumps(site.metadata_),
                site.created_at.isoformat(),
                site.updated_at.isoformat(),
            ),
        )
        return site

    def update_site(self, site: Site) -> None:
        self._conn.execute(
            """
            UPDATE sites SET name = ?, description = ?, metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                site.name,
                site.description,
                json.dumps(site.metadata_),
                site.updated_at.isoformat(),
                site.id,
            ),
        )

    def get_segment(self, site_id: str, code: str) -> NetworkSegment | None:
        row = self._conn.execute(
            "SELECT * FROM network_segments WHERE site_id = ? AND code = ?",
            (site_id, code),
        ).fetchone()
        return self._deserialize(NetworkSegment, row) if row else None

    def create_segment(self, site_id: str, payload: dict[str, Any]) -> NetworkSegment:
        segment = NetworkSegment(
            site_id=site_id,
            code=payload["code"],
            name=payload["name"],
            cidr=payload.get("cidr"),
            metadata_=payload.get("metadata", {}),
        )
        self._conn.execute(
            """
            INSERT INTO network_segments (
                id, site_id, code, name, cidr, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                segment.id,
                segment.site_id,
                segment.code,
                segment.name,
                segment.cidr,
                json.dumps(segment.metadata_),
                segment.created_at.isoformat(),
                segment.updated_at.isoformat(),
            ),
        )
        return segment

    def update_segment(self, segment: NetworkSegment) -> None:
        self._conn.execute(
            """
            UPDATE network_segments
            SET name = ?, cidr = ?, metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                segment.name,
                segment.cidr,
                json.dumps(segment.metadata_),
                segment.updated_at.isoformat(),
                segment.id,
            ),
        )

    def get_device(self, site_id: str, code: str) -> Device | None:
        row = self._conn.execute(
            "SELECT * FROM devices WHERE site_id = ? AND code = ?",
            (site_id, code),
        ).fetchone()
        return self._deserialize(Device, row) if row else None

    def create_device(self, site_id: str, payload: dict[str, Any], segment_id: str | None) -> Device:
        device = Device(
            site_id=site_id,
            segment_id=segment_id,
            code=payload["code"],
            hostname=payload["hostname"],
            ip_address=payload.get("ip_address"),
            device_type=payload.get("device_type"),
            metadata_=payload.get("metadata", {}),
        )
        self._conn.execute(
            """
            INSERT INTO devices (
                id, site_id, segment_id, code, hostname, ip_address, device_type,
                metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device.id,
                device.site_id,
                device.segment_id,
                device.code,
                device.hostname,
                device.ip_address,
                device.device_type,
                json.dumps(device.metadata_),
                device.created_at.isoformat(),
                device.updated_at.isoformat(),
            ),
        )
        return device

    def update_device(self, device: Device) -> None:
        self._conn.execute(
            """
            UPDATE devices
            SET segment_id = ?, hostname = ?, ip_address = ?, device_type = ?,
                metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                device.segment_id,
                device.hostname,
                device.ip_address,
                device.device_type,
                json.dumps(device.metadata_),
                device.updated_at.isoformat(),
                device.id,
            ),
        )

    def get_snapshot(self, service: str, snapshot_id: str) -> Snapshot | None:
        row = self._conn.execute(
            "SELECT * FROM snapshots WHERE source = ? AND external_id = ?",
            (service, snapshot_id),
        ).fetchone()
        return self._deserialize(Snapshot, row) if row else None

    def get_max_snapshot_version(self, service: str, site_id: str) -> int:
        row = self._conn.execute(
            "SELECT MAX(version) AS max_version FROM snapshots WHERE source = ? AND site_id = ?",
            (service, site_id),
        ).fetchone()
        return int(row["max_version"] or 0)

    def create_snapshot(
        self,
        *,
        service: str,
        category: str,
        payload: dict[str, Any],
        site_id: str,
        version: int,
        collected_at: datetime | None,
    ) -> Snapshot:
        snapshot = Snapshot(
            external_id=payload["snapshot_id"],
            source=service,
            category=category,
            version=version,
            site_id=site_id,
            collected_at=collected_at,
            payload=payload,
        )
        self._conn.execute(
            """
            INSERT INTO snapshots (
                id, external_id, source, category, version, site_id, collected_at,
                ingested_at, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.id,
                snapshot.external_id,
                snapshot.source,
                snapshot.category,
                snapshot.version,
                snapshot.site_id,
                snapshot.collected_at.isoformat() if snapshot.collected_at else None,
                snapshot.ingested_at.isoformat(),
                json.dumps(snapshot.payload),
            ),
        )
        return snapshot

    def _deserialize(self, model: Type[T], row: sqlite3.Row | None) -> T:
        if row is None:  # pragma: no cover - defensive
            raise ValueError("Cannot deserialize None row")
        data = dict(row)
        if "metadata" in data:
            raw = data["metadata"]
            data["metadata"] = json.loads(raw) if raw else {}
        if "payload" in data:
            data["payload"] = json.loads(data["payload"]) if data["payload"] else {}
        return model.from_row(data)  # type: ignore[return-value]
