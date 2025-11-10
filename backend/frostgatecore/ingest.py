# backend/frostgatecore/app/ingest.py
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

# Ensure shared libs are importable when executed from packaged app/
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arescore_foundry_lib.policy import (  # type: ignore
    AuditLogger,
    OpaClient,
    OpaDecisionDenied,
    PolicyBundle,
)

# Dockerfile copies only app/, so import from app.*
from app.embedding import embed_text_cached
from app.rag_cache import cached_doc_ingest

LOG = logging.getLogger("rag.ingest")

_POLICY_DIR = Path(os.getenv("POLICY_DIR", ROOT / "policies"))
_POLICY_BUNDLE = PolicyBundle.from_directory(_POLICY_DIR)
_AUDIT_LOGGER = AuditLogger.from_env(service="ingestor", default_directory=ROOT / "audits")
_OPA_CLIENT = OpaClient(bundle=_POLICY_BUNDLE, audit_logger=_AUDIT_LOGGER)
_ALLOWED_HASH = os.getenv("RUNTIME_ALLOWED_MODEL_HASH", "")
_REVOKED_RUNTIME_IDS = [s.strip() for s in os.getenv("RUNTIME_REVOKED_IDS", "").split(",") if s.strip()]

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

    runtime_id = getattr(vector_store, "runtime_id", "")
    policy_input = {
        "sig": getattr(vector_store, "signature", ""),
        "model": {"hash": getattr(vector_store, "model_hash", "")},
        "allowed": {"hash": _ALLOWED_HASH},
        "runtime": {"id": runtime_id},
        "revocation": {"runtime_ids": _REVOKED_RUNTIME_IDS},
    }

    try:
        _OPA_CLIENT.ensure_allow("foundry/runtime_revocation", policy_input)
    except OpaDecisionDenied as exc:
        LOG.warning(
            "RAG ingest denied runtime_id=%s reason=%s", runtime_id or "", exc.reason
        )
        raise PermissionError(f"ingest denied: {exc.reason or 'policy rejection'}") from exc

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
