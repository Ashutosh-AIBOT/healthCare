from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger, request_id_var

logger = get_logger("aarogya.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach X-Request-Id, measure latency, emit structured access log."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("request_error", extra={"method": request.method, "path": request.url.path})
            raise
        finally:
            request_id_var.reset(token)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        # Never log query params that may contain PHI — only path + status + latency
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", 0) if "response" in locals() else 500,  # type: ignore
                "latency_ms": elapsed_ms,
                "request_id": rid,
            },
        )
        if "response" in locals():
            response.headers["X-Request-Id"] = rid  # type: ignore
            return response  # type: ignore
        raise RuntimeError("unreachable")
