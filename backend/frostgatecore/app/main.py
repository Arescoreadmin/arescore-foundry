import os
from fastapi import FastAPI
from fastapi import FastAPI
from app.routers import ingest

app = FastAPI(title="Foundry")
app.include_router(ingest.router)


@app.get("/health")
def health():
    return {"status": "ok"}

if os.getenv("ENABLE_DEV_ROUTES", "1") == "1":
    try:
        from app.dev import router as dev_router
        app.include_router(dev_router)
    except Exception as e:
        import logging
        logging.getLogger("rag").warning("Dev router not loaded: %s", e)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
