import os
import sqlite3
import time
from typing import Optional

try:
    import redis  # type: ignore
except Exception:
    redis = None  # optional


class KVBase:
    def get(self, key: str) -> Optional[bytes]:
        raise NotImplementedError

    def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        raise NotImplementedError


class RedisKV(KVBase):
    def __init__(self, url: str):
        if redis is None:
            raise RuntimeError("redis package not installed")
        self.client = redis.from_url(url, decode_responses=False)

    def get(self, key: str) -> Optional[bytes]:
        return self.client.get(key)

    def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        if ttl:
            self.client.setex(key, ttl, value)
        else:
            self.client.set(key, value)


class SQLiteKV(KVBase):
    """
    Tiny TTL KV using SQLite. Keys and values are blobs.
    TTL is in seconds from now.
    """
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
              k TEXT PRIMARY KEY,
              v BLOB NOT NULL,
              exp INTEGER
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_kv_exp ON kv(exp)")
        self.conn.commit()

    def _purge(self):
        now = int(time.time())
        sql = "DELETE FROM kv WHERE exp IS NOT NULL AND exp < ?"
        self.conn.execute(sql, (now,))
        self.conn.commit()

    def get(self, key: str) -> Optional[bytes]:
        self._purge()
        cur = self.conn.execute("SELECT v, exp FROM kv WHERE k = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        v, exp = row
        if exp is not None and exp < int(time.time()):
            self.conn.execute("DELETE FROM kv WHERE k = ?", (key,))
            self.conn.commit()
            return None
        return v

    def set(self, key: str, value: bytes, ttl: Optional[int] = None) -> None:
        exp = int(time.time()) + ttl if ttl else None
        self.conn.execute(
            "REPLACE INTO kv(k, v, exp) VALUES (?, ?, ?)",
            (key, value, exp),
        )
        self.conn.commit()


def get_kv_from_env() -> KVBase:
    url = os.getenv("RAG_CACHE_URL", "sqlite:///data/rag_cache.sqlite3")
    if url.startswith("redis://") or url.startswith("rediss://"):
        return RedisKV(url)
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        return SQLiteKV(path)
    # default to sqlite file path
    return SQLiteKV(url)
