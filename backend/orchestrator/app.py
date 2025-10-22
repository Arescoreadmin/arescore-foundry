# add near top-level
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar

corr_id_var: ContextVar[str] = ContextVar("corr_id", default="")

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        corr_id_var.set(cid)
        request.state.corr_id = cid
        resp = await call_next(request)
        resp.headers["X-Correlation-ID"] = cid
        return resp

app.add_middleware(CorrelationIdMiddleware)

def current_corr_id() -> str:
    return corr_id_var.get()
