# backend/orchestrator/app/main.py
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Callable, Dict

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

APP_NAME = os.getenv("SERVICE_NAME", "orchestrator")

_default_origins = "http://localhost:3000"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or [_default_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip for JSON; static gzip is handled by nginx on the frontend
app.add_middleware(GZipMiddleware, minimum_size=500)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        resp = await call_next(request)
        resp.headers["x-request-id"] = rid
        return resp


class ServerTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()
        resp = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000
        resp.headers["Server-Timing"] = f"app;dur={dur_ms:.1f}"
        return resp


app.add_middleware(RequestIDMiddleware)
app.add_middleware(ServerTimingMiddleware)


@app.get("/health", include_in_schema=False)
def health() -> Dict[str, object]:
    """Liveness: process is up and can handle requests."""
    return {"status": "ok", "service": APP_NAME}


# k8s-style alias
app.add_api_route("/_healthz", health, include_in_schema=False)


@app.get("/readyz", include_in_schema=False)
async def readyz():
    """
    Readiness: return 200 only when deps are good.
    Replace placeholders with real checks (db, cache, mq).
    """
    checks: Dict[str, bool] = {}

    # TODO: add real checks here
    checks["app"] = True
    ok = True

    code = status.HTTP_200_OK
    if not ok:
        code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        {"ready": ok, "service": APP_NAME, "checks": checks},
        status_code=code,
    )


@app.on_event("startup")
async def on_startup():
    logging.getLogger(__name__).info("Startup complete for %s", APP_NAME)


@app.on_event("shutdown")
async def on_shutdown():
    logging.getLogger(__name__).info("Shutdown complete for %s", APP_NAME)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)



# --- BEGIN auto metrics wiring
# --- END auto metrics wiring

# --- BEGIN auto metrics wiring (do not edit) ---
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instr

    _EXCLUDE = {"/metrics", "/health", "/_healthz", "/readyz"}
    # Avoid double-exposing if already present (e.g., reloader)
    _already = any(getattr(r, "path", "") == "/metrics" for r in getattr(app, "routes", []))

    if not _already:
        _instr = _Instr(
            excluded_handlers=[r"^/metrics$", r"^/health$", r"^/_healthz$", r"^/readyz$"],
            should_ignore=lambda req: getattr(req, "url", None)
            and getattr(req.url, "path", "") in _EXCLUDE,
        )
        _instr.instrument(app).expose(app, include_in_schema=False)
except Exception:
    # Never block startup if metrics wiring fails
    pass
# --- END auto metrics wiring ---
# --- BEGIN managed health routes ---
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": APP_NAME}

@app.get("/readyz", include_in_schema=False)
async def readyz():
    # TODO: add real dependency checks here
    ok = True
    code = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse({"ready": ok, "service": APP_NAME}, status_code=code)

# Keep Kubernetes-style alias available
try:
    _paths = [getattr(r, "path", "") for r in getattr(app, "routes", [])]
    if "/_healthz" not in _paths:
        app.add_api_route("/_healthz", health, include_in_schema=False)
except Exception:
    pass
# --- END managed health routes ---
