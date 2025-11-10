"""FastAPI application factory for ingestor services."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .audit import AuditLogger
from .database import Session, create_db_engine, create_session_factory, initialize_database
from .events import EventPublisher, LoggingEventPublisher
from .ingest import ingest_snapshot
from .validation import SnapshotValidator, ValidationError

DEFAULT_AUDIT_DIR = Path(os.getenv("FOUNDRY_AUDIT_DIR", "audits"))
DEFAULT_EVENT_SUBJECT = "snapshot.synced"


def load_schema(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def create_ingestor_app(
    *,
    service_name: str,
    schema_path: str | Path,
    snapshot_category: str,
    event_subjects: Optional[Iterable[str]] = None,
    database_url: str | None = None,
    audit_log_path: Path | None = None,
    event_publisher: EventPublisher | None = None,
) -> FastAPI:
    """Create and configure a FastAPI application for ingestion."""

    schema = load_schema(schema_path)
    validator = SnapshotValidator(schema)

    engine = create_db_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    audit_path = audit_log_path or DEFAULT_AUDIT_DIR / f"{service_name}.jsonl"
    audit_logger = AuditLogger(audit_path)

    publisher = event_publisher or LoggingEventPublisher()
    subjects = list(event_subjects or [DEFAULT_EVENT_SUBJECT, f"snapshot.{snapshot_category}.synced"])

    app = FastAPI(title=service_name)
    app.state.session_factory = session_factory
    app.state.validator = validator
    app.state.audit_logger = audit_logger
    app.state.publisher = publisher
    app.state.event_subjects = subjects
    app.state.service_name = service_name
    app.state.snapshot_category = snapshot_category

    def get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @app.post("/sync", status_code=202)
    async def sync_endpoint(payload: dict[str, Any], db: Session = Depends(get_db)) -> JSONResponse:
        snapshot_id = payload.get("snapshot_id")
        try:
            validator.validate(payload)
        except ValidationError as exc:
            audit_logger.log(
                service=service_name,
                snapshot_id=snapshot_id,
                status="failed",
                details={"error": str(exc)},
            )
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            snapshot, created = ingest_snapshot(
                db,
                service=service_name,
                category=snapshot_category,
                payload=payload,
            )
        except ValueError as exc:
            audit_logger.log(
                service=service_name,
                snapshot_id=snapshot_id,
                status="failed",
                details={"error": str(exc)},
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        db.commit()

        audit_logger.log(
            service=service_name,
            snapshot_id=snapshot.external_id,
            status="ingested" if created else "duplicate",
            details={"version": snapshot.version},
        )

        if created:
            event_payload = {
                "snapshot_id": snapshot.external_id,
                "source": service_name,
                "category": snapshot_category,
                "version": snapshot.version,
                "site_id": snapshot.site_id,
            }

            for subject in subjects:
                await publisher.publish(subject, event_payload)

        return JSONResponse({"status": "accepted", "version": snapshot.version}, status_code=202)

    return app
