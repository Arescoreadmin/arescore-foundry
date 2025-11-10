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
    Base.metadata.create_all(bind=engine)


app.include_router(health.router)
app.include_router(plans.router)
app.include_router(tenants.router)
app.include_router(users.router)
app.include_router(templates.router)
app.include_router(spawn.router)
