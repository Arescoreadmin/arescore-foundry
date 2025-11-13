from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header
from typing import Optional
import os, hashlib, tempfile
from datetime import timedelta

router = APIRouter(prefix="/api", tags=["ingest"])

# ---- Config ----
MAX_UPLOAD_BYTES = int(os.getenv("INGEST_MAX_BYTES", str(50 * 1024 * 1024)))
ALLOW_CONTENT_TYPES = set(
    os.getenv("INGEST_ALLOW_CT", "application/pdf,text/plain,image/png,image/jpeg").split(",")
)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
DEFAULT_BUCKET = os.getenv("MINIO_BUCKET", "ingest")
ENABLE_PRESIGNED = os.getenv("INGEST_PRESIGNED", "false").lower() == "true"
PRESIGNED_EXPIRY_SEC = int(os.getenv("INGEST_PRESIGNED_EXP", "900"))

# ---- Test hook (used only by tests) ----
_TEST_FAKE_CLIENT = None
def _set_test_fake_client(fake):
    global _TEST_FAKE_CLIENT
    _TEST_FAKE_CLIENT = fake

def get_minio() -> object:
    # If tests set a fake, return it during dependency resolution
    if _TEST_FAKE_CLIENT is not None:
        return _TEST_FAKE_CLIENT
    from minio import Minio
    return Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=MINIO_SECURE)

def ensure_bucket(client: object, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        try:
            client.set_bucket_versioning(bucket, "Enabled")
        except Exception:
            pass

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    content_length: Optional[int] = Header(default=None),
    tenant: Optional[str] = Header(default=None),
    client = Depends(get_minio),
) -> dict:
    # Safety: if a fake was set after dependency resolution, still honor it
    if _TEST_FAKE_CLIENT is not None:
        client = _TEST_FAKE_CLIENT

    bucket = (tenant or "").strip() or DEFAULT_BUCKET
    object_name = file.filename or "unnamed"

    if content_length is not None and content_length > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_UPLOAD_BYTES} bytes.")

    if file.content_type and ALLOW_CONTENT_TYPES and file.content_type not in ALLOW_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content-type {file.content_type}")

    try:
        ensure_bucket(client, bucket)

        hasher = hashlib.sha256()
        total = 0
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as spooled:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_UPLOAD_BYTES} bytes.")
                hasher.update(chunk)
                spooled.write(chunk)

            checksum = hasher.hexdigest()
            spooled.seek(0)

            put_result = client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=spooled,
                length=total,
                content_type=file.content_type or None,
            )

        resp = {
            "bucket": bucket,
            "object": object_name,
            "size": total,
            "sha256": checksum,
        }

        if put_result is not None:
            etag = getattr(put_result, "etag", None)
            version_id = getattr(put_result, "version_id", None)
            if etag:
                resp["etag"] = etag
            if version_id:
                resp["version_id"] = version_id

        if ENABLE_PRESIGNED:
            url = client.get_presigned_url(
                "GET", bucket, object_name, expires=timedelta(seconds=PRESIGNED_EXPIRY_SEC)
            )
            resp["presigned_get"] = url
            resp["presigned_get_expires_sec"] = PRESIGNED_EXPIRY_SEC

        return resp

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal ingest failure")
