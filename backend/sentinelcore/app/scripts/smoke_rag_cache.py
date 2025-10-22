import os
os.environ.setdefault("RAG_CACHE_URL", "sqlite:///data/rag_cache.sqlite3")
os.environ.setdefault("RAG_QUERY_TTL_SECONDS", "5")

from sentinelcore.rag_cache import Cache

calls = {"ingest": 0, "embed": 0, "query": 0}

def fake_ingest(doc: bytes) -> str:
    calls["ingest"] += 1
    return f"doc-{len(doc)}"

def fake_embed(text: str):
    calls["embed"] += 1
    # pretend your model returns a 3-dim vector
    return [float(len(text)), 1.0, 0.0]

def fake_query(q: str, k: int):
    calls["query"] += 1
    return [f"id-{i}" for i in range(k)]

c = Cache()

doc = b"Hello there. " * 10
d1 = c.cached_doc_ingest(doc, fake_ingest)
d2 = c.cached_doc_ingest(doc, fake_ingest)
assert d1 == d2, "doc idempotency failed"

t = "The quick brown fox jumps over the lazy dog."
e1 = c.cached_embed(fake_embed, t)
e2 = c.cached_embed(fake_embed, t)
assert e1 == e2, "embed cache failed"

q1 = c.cached_query_topk(fake_query, "brown fox", 5)
q2 = c.cached_query_topk(fake_query, "brown   fox", 5)
assert q1 == q2, "query normalization/TTL cache failed"

print("OK:", calls)  # expect low call counts, e.g., each path invoked once
