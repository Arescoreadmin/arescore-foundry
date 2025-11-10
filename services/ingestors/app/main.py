import io
import os
import uuid
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error

app = FastAPI(title="ingestors")


def _minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true", "yes"}
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(client: Minio, bucket: str) -> None:
    if client.bucket_exists(bucket):
        return
    client.make_bucket(bucket)


@app.on_event("startup")
def startup() -> None:
    bucket = os.getenv("MINIO_BUCKET", "scenarios")
    client = _minio_client()
    ensure_bucket(client, bucket)


@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/ready")
def ready() -> Dict[str, bool]:
    try:
        client = _minio_client()
        bucket = os.getenv("MINIO_BUCKET", "scenarios")
        ensure_bucket(client, bucket)
    except S3Error as exc:  # pragma: no cover - network call
        raise HTTPException(status_code=502, detail=f"MinIO unavailable: {exc}")
    return {"ok": True}


@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)) -> Dict[str, Optional[str]]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty payload")

    object_name = f"{uuid.uuid4()}-{file.filename or 'payload'}"
    bucket = os.getenv("MINIO_BUCKET", "scenarios")
    client = _minio_client()

    try:
        data_stream = io.BytesIO(data)
        client.put_object(bucket, object_name, data_stream, length=len(data))
    except S3Error as exc:  # pragma: no cover - network call
        raise HTTPException(status_code=502, detail=f"Upload failed: {exc}")

    control_plane_api = os.getenv("CONTROL_PLANE_SCENARIO_API")
    if control_plane_api:
        payload = {
            "object": object_name,
            "bucket": bucket,
            "filename": file.filename,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(control_plane_api, json=payload)
        except httpx.RequestError as exc:  # pragma: no cover - network call
            raise HTTPException(status_code=502, detail=f"Control plane sync failed: {exc}")

    return {"object": object_name, "bucket": bucket}
