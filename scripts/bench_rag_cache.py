import os
import time

from frostgatecore.rag_cache import Cache


os.environ.setdefault("RAG_CACHE_URL", "sqlite:///data/rag_cache.sqlite3")

calls = {"embed": 0}
def slow_embed(t: str):
    calls["embed"] += 1
    time.sleep(0.25)  # simulate slow model
    return [float(len(t))]

c = Cache()
text = "lorem ipsum " * 200

t0 = time.perf_counter()
v1 = c.cached_embed(slow_embed, text)
t1 = time.perf_counter()
v2 = c.cached_embed(slow_embed, text)
t2 = time.perf_counter()

print(f"embed calls={calls['embed']}  first={t1-t0:.3f}s  second={t2-t1:.3f}s  speedup={(t1-t0)/(t2-t1 + 1e-6):.1f}x")
