"""Placeholder service implementation."""
from fastapi import FastAPI

app = FastAPI(title="Ot Lab")


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/metrics')
def metrics():
    return {'pack_up': 1}
