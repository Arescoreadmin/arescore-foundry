"""FastAPI application for the identity ingestor."""

from __future__ import annotations

from pathlib import Path

from services.foundry_ingestor_common import create_ingestor_app

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "identity_snapshot.schema.json"

app = create_ingestor_app(
    service_name="foundry-identity-ingestor",
    schema_path=SCHEMA_PATH,
    snapshot_category="identity",
)
