from fastapi import FastAPI

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401
from .routers import health, plans, spawn, tenants, templates, users

settings = get_settings()

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

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Service responsible for orchestrating tenant-scoped scenario spawns.",
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(health.router)
app.include_router(plans.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(spawn.router)
