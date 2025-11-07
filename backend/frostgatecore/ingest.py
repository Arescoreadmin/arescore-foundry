# backend/frostgatecore/app/ingest.py
import logging
from typing import Iterable, Tuple, Optional

# Dockerfile copies only app/, so import from app.*
from app.rag_cache import cached_doc_ingest
from app.embedding import embed_text_cached

LOG = logging.getLogger("rag.ingest")

# Try to pick up correlation ID from orchestrator if that package is available on PYTHONPATH.
# If not, we fall back to "local" so this module doesn't crash in isolation.
def _safe_current_corr_id() -> Optional[str]:
    try:
        from orchestrator.app import current_corr_id  # type: ignore
        return current_corr_id()
    except Exception:
        return None


def ingest_doc_idempotent(doc_bytes: bytes, vector_store) -> str:
    """
    Idempotently ingest a raw document and return the stable doc_id.

    Parameters
    ----------
    doc_bytes : bytes
        Raw document content.
    vector_store :
        Store with an `ingest(doc_bytes: bytes) -> str` method that returns doc_id.
    """
    cid = _safe_current_corr_id() or "local"
    doc_id = cached_doc_ingest(doc_bytes, ingest_fn=vector_store.ingest)
    LOG.info("RAGCACHE ingest corr_id=%s doc_id=%s bytes=%d", cid, doc_id, len(doc_bytes))
    return doc_id


def upsert_chunks_with_cache(
    doc_id: str,
    chunks: Iterable[Tuple[str, str]],
    embedder,
    vector_store,
) -> int:
    """
    Upsert chunk embeddings with caching.

    Parameters
    ----------
    doc_id : str
        Document identifier returned by `ingest_doc_idempotent`.
    chunks : Iterable[Tuple[str, str]]
        Iterable of (chunk_id, chunk_text).
    embedder :
        Object exposing `embed_text(text: str) -> list[float]` or similar.
    vector_store :
        Store exposing `upsert_embedding(doc_id: str, chunk_id: str, embedding) -> None`.

    Returns
    -------
    int
        Number of chunks upserted.
    """
    count = 0
    cid = _safe_current_corr_id() or "local"

    for chunk_id, chunk_text in chunks:
        emb = embed_text_cached(chunk_text, embed_fn=embedder.embed_text)
        vector_store.upsert_embedding(doc_id, chunk_id, emb)
        count += 1

    LOG.info("RAGCACHE upsert corr_id=%s doc_id=%s chunks=%d", cid, doc_id, count)
    return count
