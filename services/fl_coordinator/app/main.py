from fastapi import FastAPI

from arescore_foundry_lib.logging_setup import configure_logging
configure_logging()

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from arescore_foundry_lib.logging_setup import _request_id_ctx, get_request_id
import logging, uuid
logger = logging.getLogger("request")

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        _request_id_ctx.set(str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = get_request_id()
        logger.info(f"{request.method} {request.url.path} -> {response.status_code}")
        return response

app = FastAPI(title="{{SERVICE_NAME}}".replace("{{SERVICE_NAME}}", __name__.split(".")[0]))

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/live")
def live():
    return {"status": "alive"}

@app.get("/ready")
def ready():
    # future: check dependencies here (DB, message bus, etc.)
    return {"status": "ready"}
