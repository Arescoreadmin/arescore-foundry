from fastapi import FastAPI

app = FastAPI()

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=false)
except Exception as _e:
    # metrics optional; don't crash app if lib missing
    pass


@app.get("/health")
async def health():
    return {"status": "ok"}

# --- injected by scripts/fix_api_health.sh ---
try:
    from fastapi import FastAPI  # type: ignore
except Exception:
    pass  # FastAPI may already be imported elsewhere

try:
    app  # type: ignore  # noqa: F821
except NameError:
    app = FastAPI()

@app.get("/_healthz", include_in_schema=False)
def _root_health():
    return {"status": "ok"}
# --- end injected block ---

# --- BEGIN: injected request-id middleware ---
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

async def _rid_mw(request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

try:
    app.add_middleware(BaseHTTPMiddleware, dispatch=_rid_mw)
except Exception:
    pass
# --- END: injected request-id middleware ---
