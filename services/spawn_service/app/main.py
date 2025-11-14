from fastapi import FastAPI

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401
from .routers import health, plans, spawn, tenants, templates, users

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Service responsible for orchestrating tenant-scoped scenario spawns.",
)


@app.on_event("startup")
def startup() -> None:
    # Ensure tables exist; safe for SQLite dev
    Base.metadata.create_all(bind=engine)


# Health router: /health, /health/live, /health/ready
app.include_router(health.router)

# Business routers
app.include_router(plans.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(spawn.router)
