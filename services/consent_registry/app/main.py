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

app = FastAPI(title="consent_registry")

@app.get("/health")
def health(): return {"ok": True}

@app.get("/live")
def live(): return {"status": "alive"}

@app.get("/ready")
def ready(): return {"status": "ready"}

# Expected by smokes:
@app.post("/consent/training/optin")
def training_optin():
    # TODO: persist subject/token, etc.
    return {"status": "opted_in", "subject": None}

@app.get("/crl")
def crl():
    # TODO: wire to real CRL backing store
    return {"serials": []}
