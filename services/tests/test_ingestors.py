import io
import os
import pytest
from fastapi.testclient import TestClient

# Import the app and the factory we’ll monkeypatch
from services.ingestors.app.main import app, minio_client

client = TestClient(app)

class FakeMinio:
    def __init__(self):
        self.buckets = set()
        self.objects = {}

    def bucket_exists(self, name):
        return name in self.buckets

    def make_bucket(self, name):
        self.buckets.add(name)

    def put_object(self, bucket, key, body, length, content_type=None, metadata=None):
        # Read provided stream safely
        data = body.read(length)
        assert len(data) == length
        self.objects[(bucket, key)] = {
            "data": data,
            "content_type": content_type,
            "metadata": metadata or {},
        }
        class R:  # minimal shape like MinIO’s response
            etag = "fake-etag"
            version_id = "v1"
        return R()

@pytest.fixture(autouse=True)
def patch_minio(monkeypatch):
    fake = FakeMinio()
    monkeypatch.setenv("INGEST_BUCKET", "ingest")
    monkeypatch.setenv("INGEST_MAX_BYTES", str(1024 * 1024))  # 1 MB
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    # Replace the client factory
    monkeypatch.setattr("services.ingestors.app.main.minio_client", lambda: fake)
    return fake

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_ingest_success(patch_minio):
    content = b"hello world"
    files = {"file": ("hello.txt", io.BytesIO(content), "text/plain")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["bucket"] == "ingest"
    assert body["object"] == "hello.txt"
    assert body["size"] == str(len(content))
    assert body["sha256"]  # present
    # stored content matches
    stored = patch_minio.objects[("ingest", "hello.txt")]
    assert stored["data"] == content
    assert stored["content_type"] == "text/plain"
    assert "X-Request-ID" in stored["metadata"]

def test_empty_file_rejected():
    files = {"file": ("empty.bin", io.BytesIO(b""), "application/octet-stream")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 400
    assert r.json()["error"] is True

def test_too_large_rejected(monkeypatch):
    monkeypatch.setenv("INGEST_MAX_BYTES", "5")
    files = {"file": ("big.bin", io.BytesIO(b"123456"), "application/octet-stream")}
    r = client.post("/api/ingest", files=files)
    assert r.status_code == 413

def test_override_bucket_and_key(patch_minio):
    files = {"file": ("name.txt", io.BytesIO(b"abc"), "text/plain")}
    r = client.post("/api/ingest?bucket=tenant-a&object_name=custom/key.txt", files=files)
    assert r.status_code == 200
    assert patch_minio.objects[("tenant-a", "custom/key.txt")]["data"] == b"abc"
