from fastapi import FastAPI

from .routers import health


app = FastAPI(
    title="Foundry Orchestrator (MVP)",
    version="0.0.1",
    description="Slim orchestrator exposing basic health endpoints for CI smokes.",
)

# Health router: /health, /health/live, /health/ready
app.include_router(health.router)
