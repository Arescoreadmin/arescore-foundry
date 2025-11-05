import logging
from .corr import current_corr_id
from app.rag_cache.cache import cached_embed  # direct import avoids __init__ export issues

LOG = logging.getLogger("rag.embed")

def embed_text_cached(text: str, embed_fn):
    cid = current_corr_id()
    vec = cached_embed(text, embed_fn=embed_fn)
    LOG.info("RAGCACHE embed hit corr_id=%s len=%d", cid, len(text))
    return vec
