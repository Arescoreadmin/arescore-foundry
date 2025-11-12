import io
import os
import uuid
from typing import Dict, Optional

from fastapi.responses import JSONResponse
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error

from arescore_foundry_lib.logging_setup import configure_logging
configure_logging()

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from arescore_foundry_lib.logging_setup import _request_id_ctx, get_request_id
import logging, uuid
logger = logging.getLogger("request")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        _request_id_ctx.set(str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response

app = FastAPI(title="ingestors")

_ready = False


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
    global _ready
    _ready = True


@app.get("/health", tags=["meta"])
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/ready", tags=["meta"])
def ready() -> JSONResponse:
    try:
        client = _minio_client()
        bucket = os.getenv("MINIO_BUCKET", "scenarios")
        ensure_bucket(client, bucket)
        return JSONResponse({"status": "ready"})
    except Exception as exc:  # broader catch to avoid crashing on non-S3 errors
        raise HTTPException(status_code=502, detail=f"MinIO unavailable: {exc}")


@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)) -> Dict[str, Optional[str]]:
    ...
    client = _minio_client()
    try:
        ensure_bucket(client, bucket)   # lazy create
        data_stream = io.BytesIO(data)
        client.put_object(bucket, object_name, data_stream, length=len(data))
    except Exception as exc:
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
