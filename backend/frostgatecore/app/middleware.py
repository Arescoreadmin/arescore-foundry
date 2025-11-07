from starlette.middleware.base import BaseHTTPMiddleware
from .corr import set_corr_id
import uuid

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        set_corr_id(cid)
        resp = await call_next(request)
        resp.headers["X-Correlation-ID"] = cid
        return resp
