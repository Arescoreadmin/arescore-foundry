from fastapi import FastAPI

from .routers.orchestrate import router as orchestrate_router

def create_app() -> FastAPI:
    app = FastAPI(title="FrostGate Orchestrator", version="0.1.0")
    # Attach orchestrator routes
    app.include_router(orchestrate_router, prefix="/api/orchestrator", tags=["orchestrator"])
    return app

app = create_app()
