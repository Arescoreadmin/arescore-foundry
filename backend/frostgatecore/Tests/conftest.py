from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from app.rag_cache.cache import Cache
from app.rag_cache import cache as cache_module
from app.rag_cache.kv import KVBase


class _MockResponse:
    def __init__(self, status_code: int = 200, payload: dict[str, object] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {"status": "ok"}

    def json(self) -> dict[str, object]:
        return self._payload


@pytest.fixture(autouse=True)
def _mock_frostgatecore_health(monkeypatch: pytest.MonkeyPatch) -> None:
    original_get = httpx.get

    def fake_get(url: str, *args, **kwargs):
        if url.startswith("http://127.0.0.1:8001") and url.endswith("/health"):
            return _MockResponse()
        return original_get(url, *args, **kwargs)

    monkeypatch.setattr(httpx, "get", fake_get)
    yield
    monkeypatch.setattr(httpx, "get", original_get)


@pytest.fixture(autouse=True)
def _isolate_rag_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache_path = tmp_path / "rag_cache.sqlite3"
    monkeypatch.setenv("RAG_CACHE_URL", f"sqlite:///{cache_path}")
    yield
    if cache_path.exists():
        cache_path.unlink()


class _MemoryKV(KVBase):
    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, float | None]] = {}

    def get(self, key: str) -> bytes | None:
        entry = self._store.get(key)
        if not entry:
            return None
        value, exp = entry
        if exp is not None and exp < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        expiry = time.time() + ttl if ttl else None
        self._store[key] = (value, expiry)


@pytest.fixture(autouse=True)
def _inmemory_rag_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Cache(kv=_MemoryKV(), query_ttl_seconds=120)
    monkeypatch.setattr(cache_module, "_cache_singleton", cache)
    yield
    monkeypatch.setattr(cache_module, "_cache_singleton", None)
