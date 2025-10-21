# backend/sentinelcore/app/main.py
from fastapi import FastAPI, Body, Query, Request
from pydantic import BaseModel
from typing import Callable, Dict, Any, List
import logging, sys, time, uuid, contextvars

# -----------------------------------------------------------------------------
# Logging that actually prints
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
LOG = logging.getLogger("rag")

# -----------------------------------------------------------------------------
# Correlation ID middleware (self-contained)
# -----------------------------------------------------------------------------
_corr_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("corr_id", default="")

def current_corr_id() -> str:
    cid = _corr_id_var.get()
    return cid or "unknown"

class CorrelationIdMiddleware:
    def __init__(self, app: FastAPI, request_header: str = "X-Correlation-ID", fallback_header: str = "X-Request-Id", response_header: str = "X-Correlation-ID"):
        self.app = app
        self.request_header = request_header
        self.fallback_header = fallback_header
        self.response_header = response_header

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        corr = headers.get(self.request_header.lower()) or headers.get(self.fallback_header.lower()) or str(uuid.uuid4())
        token = _corr_id_var.set(corr)

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                headers_list = message.setdefault("headers", [])
                headers_list.append((self.response_header.encode(), corr.encode()))
            await send(message)

        try:
            return await self.app(scope, receive, send_with_header)
        finally:
            _corr_id_var.reset(token)

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

@app.get("/health")
def health():
    return {"ok": True}

# -----------------------------------------------------------------------------
# RAG cache demo endpoints
# -----------------------------------------------------------------------------
from app.rag_cache import cached_embed, cached_query_topk  # now exported correctly

class EmbedReq(BaseModel):
    text: str

def _fake_embed(t: str) -> List[float]:
    # Replace with your real embedder, e.g. embedder.embed_text
    return [float(len(" ".join(t.split())))]  # pretend normalized

def _fake_search(query_vec: List[float], top_k: int):
    # Replace with your real vector store search
    return [{"doc_id": i, "score": 1.0 / (i + 1)} for i in range(top_k)]

@app.post("/dev/embed")
def dev_embed(req: EmbedReq):
    cid = current_corr_id()
    vec = cached_embed(req.text, embed_fn=_fake_embed)
    logging.getLogger("rag.embed").info("RAGCACHE embed hit corr_id=%s len=%d", cid, len(req.text))
    return {"vec": vec}

@app.get("/dev/q")
def dev_q(q: str = Query(...), k: int = 5):
    cid = current_corr_id()
    # correct arg order: query, query_fn, k
    hits = cached_query_topk(q, _fake_search, k)
    logging.getLogger("rag.query").info(
        "RAGCACHE query hit corr_id=%s q=%r k=%d", cid, q, k
    )
    return {"hits": hits}
