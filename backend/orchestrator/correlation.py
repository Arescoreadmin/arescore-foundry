"""Correlation ID helpers for the orchestrator service."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Callable, Awaitable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

corr_id_var: ContextVar[str] = ContextVar("corr_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        corr_id_var.set(correlation_id)
        request.state.corr_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def install_correlation_middleware(app: FastAPI) -> None:
    """Attach the correlation ID middleware to the given FastAPI app."""

    app.add_middleware(CorrelationIdMiddleware)


def current_corr_id() -> str:
    """Return the correlation ID for the current request context."""

    return corr_id_var.get()


__all__ = [
    "CorrelationIdMiddleware",
    "install_correlation_middleware",
    "current_corr_id",
]
