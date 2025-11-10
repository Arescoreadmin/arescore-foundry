from app.rag_cache import cached_embed, cached_query_topk

def fake_embed(text: str) -> str:
    return f"vec:{text}"


def test_embed_normalizes_whitespace():
    a = cached_embed("hello   world", embed_fn=fake_embed)
    b = cached_embed("hello world", embed_fn=fake_embed)
    assert a == b

def test_query_ttl_hit():
    calls = {"n": 0}
    def fake(q, k):
        calls["n"] += 1
        return [("doc", 1.0)] * k
    r1 = cached_query_topk(query="q", k=3, query_fn=fake)
    r2 = cached_query_topk(query="q", k=3, query_fn=fake)
    assert r1 == r2
    assert calls["n"] == 1
