import logging
from frostgatecore.rag_cache import cached_query_topk
from orchestrator.app import current_corr_id

LOG = logging.getLogger("rag.search")

def search_topk_cached(vector_store, query: str, k: int = 10):
    cid = current_corr_id() or "local"
    ids = cached_query_topk(query, query_fn=lambda q, kk: vector_store.similarity_search(q, top_k=kk), k=k)
    LOG.info("RAGCACHE query hit corr_id=%s k=%d", cid, k)
    return ids
