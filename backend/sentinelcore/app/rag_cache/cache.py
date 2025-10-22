# backend/sentinelcore/app/rag_cache/cache.py
from __future__ import annotations

import os
from typing import Any, Callable, List, Optional, Mapping, Sequence

from .kv import get_kv_from_env, KVBase
from .utils import sha256_text, sha256_bytes, normalize_text

# ---------- JSON helpers (prefer orjson if present) ----------
try:
    import orjson as _json  # type: ignore
    def _json_dumps(obj: Any) -> bytes:
        return _json.dumps(obj, option=_json.OPT_SERIALIZE_NUMPY)
    def _json_loads(b: bytes) -> Any:
        return _json.loads(b)
except Exception:  # pragma: no cover
    import json as _json  # type: ignore
    def _json_dumps(obj: Any) -> bytes:
        return _json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    def _json_loads(b: bytes) -> Any:
        return _json.loads(b.decode('utf-8'))

# ---------- normalization without JSON round-trip ----------
_JSON_ATOMS = (str, int, float, bool, type(None))

def _to_jsonable(x: Any) -> Any:
    if isinstance(x, _JSON_ATOMS):
        return x
    if isinstance(x, bytes):
        return x.decode('utf-8', errors='replace')
    if isinstance(x, Mapping):
        return {k: _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, Sequence) and not isinstance(x, (str, bytes, bytearray)):
        return [_to_jsonable(v) for v in x]
    return str(x)

EmbVector = List[float]

class Cache:
    __slots__ = ('kv','query_ttl_s','ns','_prefix')

    def __init__(
        self,
        kv: Optional[KVBase] = None,
        query_ttl_seconds: Optional[int] = None,
        namespace: Optional[str] = None,
    ) -> None:
        self.kv = kv or get_kv_from_env()
        self.query_ttl_s = int(os.getenv('RAG_QUERY_TTL_SECONDS', str(query_ttl_seconds or 90)))
        self.ns = (namespace or os.getenv('RAG_CACHE_NAMESPACE', '')).strip(':')
        self._prefix = f'{self.ns}:' if self.ns else ''

    # keys
    def k_doc(self, doc_hash: str) -> str:   return f'{self._prefix}doc:{doc_hash}'
    def k_chunk(self, chunk_hash: str) -> str: return f'{self._prefix}chunk:{chunk_hash}'
    def k_query(self, q_hash: str) -> str:   return f'{self._prefix}q:{q_hash}'

    # KV wrappers
    def _kv_get(self, key: str) -> Optional[bytes]:
        try:
            v = self.kv.get(key)
            if v is None:
                return None
            if isinstance(v, bytes):
                return v
            if isinstance(v, str):
                return v.encode('utf-8')
            return str(v).encode('utf-8')
        except Exception:
            return None

    def _kv_set(self, key: str, value: bytes, ttl_s: Optional[int] = None) -> None:
        try:
            if ttl_s is not None:
                return self.kv.set(key, value, ttl=ttl_s)  # type: ignore[arg-type]
            return self.kv.set(key, value)                 # type: ignore[misc]
        except TypeError:
            if ttl_s is not None:
                try:
                    return self.kv.set(key, value, ex=ttl_s)  # type: ignore[misc]
                except Exception:
                    pass
            try:
                return self.kv.set(key, value)  # type: ignore[misc]
            except Exception:
                return None

    # doc ingest idempotency
    def cached_doc_ingest(self, doc_bytes: bytes, ingest_fn: Callable[[bytes], str]) -> str:
        h = sha256_bytes(doc_bytes)
        key = self.k_doc(h)
        hit = self._kv_get(key)
        if hit:
            return hit.decode('utf-8')
        doc_id = ingest_fn(doc_bytes)
        self._kv_set(key, doc_id.encode('utf-8'))
        return doc_id

    # chunk embedding
    def cached_embed(self, text: str, embed_fn: Callable[[str], EmbVector]) -> EmbVector:
        t   = normalize_text(text)
        key = self.k_chunk(sha256_text(t))
        hit = self._kv_get(key)
        if hit:
            return _json_loads(hit)
        vec = embed_fn(t)
        norm_vec = _to_jsonable(vec)
        self._kv_set(key, _json_dumps(norm_vec))
        return norm_vec

    # query topK
    def cached_query_topk(self, query: str, k: int, query_fn: Callable[[str, int], List[Any]]) -> List[Any]:
        qn  = normalize_text(query)
        key = self.k_query(sha256_text(f'{qn}|k={k}'))
        hit = self._kv_get(key)
        if hit:
            return _json_loads(hit)
        results = query_fn(qn, k)
        norm    = _to_jsonable(results)
        self._kv_set(key, _json_dumps(norm), ttl_s=self.query_ttl_s)
        return norm

# module-level singleton + helpers
_cache_singleton: Optional[Cache] = None
def _cache() -> Cache:
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = Cache()
    return _cache_singleton

def cached_doc_ingest(doc_bytes: bytes, ingest_fn: Callable[[bytes], str]) -> str:
    return _cache().cached_doc_ingest(doc_bytes, ingest_fn)

def cached_embed(text: str, embed_fn: Callable[[str], EmbVector]) -> EmbVector:
    return _cache().cached_embed(text, embed_fn)

def cached_query_topk(query: str, k: int, query_fn: Callable[[str, int], List[Any]]) -> List[Any]:
    return _cache().cached_query_topk(query, k, query_fn)

__all__ = ['Cache','cached_doc_ingest','cached_embed','cached_query_topk']
