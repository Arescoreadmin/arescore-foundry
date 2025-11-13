# services/ingestors/app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import os
import io
import uuid
import hashlib
import logging

from minio import Minio
from minio.error import S3Error

# ---- Observability: JSON logs + request correlation ----
from arescore_foundry_lib.logging_setup import configure_logging, _request_id_ctx, get_request_id

configure_logging()
logger = logging.getLogger("ingestors")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        _request_id_ctx.set(str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        logging.getLogger("request").info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response

app = FastAPI(title="ingestors")
app.add_middleware(RequestIDMiddleware)

# ---- Config via env with sane defaults ----
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
DEFAULT_BUCKET = os.getenv("INGEST_BUCKET", "ingest")
MAX_UPLOAD_BYTES = int(os.getenv("INGEST_MAX_BYTES", str(50 * 1024 * 1024)))  # 50MB default


def minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/ingest")
async def ingest_document(
    file: UploadFile = File(..., description="File to ingest into object storage"),
    bucket: Optional[str] = None,
    object_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    Ingest a file into MinIO.

    Query params:
      - bucket: override target bucket (default from env/`ingest`)
      - object_name: override object key (defaults to uploaded filename or UUID)
    """
    target_bucket = (bucket or DEFAULT_BUCKET).strip()
    if not target_bucket:
        raise HTTPException(status_code=400, detail="Bucket name cannot be empty.")

    # Determine object name
    key = (object_name or file.filename or f"upload-{uuid.uuid4().hex}").strip()

    try:
        # Read the upload into memory; enforce size limit
        data = await file.read()
        if len(data) == 0:
            raise HTTPException(status_code=400, detail="Empty file.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large (> {MAX_UPLOAD_BYTES} bytes).")

        # Prepare upload
        client = minio_client()
        ensure_bucket(client, target_bucket)

        content_type = file.content_type or "application/octet-stream"
        body = io.BytesIO(data)
        digest = sha256_bytes(data)
        req_id = get_request_id() or ""

        # Upload (MinIO needs exact length)
        result = client.put_object(
            target_bucket,
            key,
            body,
            length=len(data),
            content_type=content_type,
            metadata={
                "X-Request-ID": req_id,
                "X-SHA256": digest,
                "X-Original-Filename": file.filename or "",
            },
        )

        logger.info(
            "ingest_ok",
            extra={
                "bucket": target_bucket,
                "object": key,
                "size": len(data),
                "etag": getattr(result, "etag", None),
                "version_id": getattr(result, "version_id", None),
                "request_id": req_id,
                "sha256": digest,
                "content_type": content_type,
            },
        )

        return {
            "bucket": target_bucket,
            "object": key,
            "size": str(len(data)),
            "etag": getattr(result, "etag", ""),
            "version_id": getattr(result, "version_id", ""),
            "sha256": digest,
            "content_type": content_type,
            "request_id": req_id,
        }

    except HTTPException:
        raise
    except S3Error as s3e:
        logger.exception("minio_error")
        raise HTTPException(status_code=502, detail=f"MinIO error: {s3e.code}")
    except Exception as exc:
        logger.exception("ingest_unexpected_error")
        raise HTTPException(status_code=500, detail="Unexpected error during ingest.")  # do not leak internals


# Optional: nicer JSON error shape
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status": exc.status_code,
            "detail": exc.detail,
            "request_id": get_request_id() or "",
        },
    )
