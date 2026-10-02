"""Middleware that gives every request an id, logs it with its status and duration, and logs failures."""

import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from casm.api.logging_config import request_id_var

logger: logging.Logger = logging.getLogger("casm.api.request")
REQUEST_ID_HEADER: str = "X-Request-ID"
MAX_ID_LENGTH: int = 64


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One INFO line per request (WARNING for a 4xx, ERROR for a 5xx), and a JSON 500 for an unhandled error.

    The id comes from the caller's `X-Request-ID` header when present, otherwise it is generated, and it is
    returned in the response so a client can quote it.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        supplied: str = request.headers.get(REQUEST_ID_HEADER, "").strip()[:MAX_ID_LENGTH]
        request_id: str = supplied or uuid4().hex[:12]
        token = request_id_var.set(request_id)
        started: float = time.perf_counter()
        target: str = request.url.path + (
            f"?{request.url.query}" if request.url.query else ""
        )
        try:
            try:
                response: Response = await call_next(request)
            except Exception:
                elapsed: float = (time.perf_counter() - started) * 1000
                logger.exception(
                    "%s %s -> 500 unhandled error (%.1f ms)",
                    request.method,
                    target,
                    elapsed,
                )
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal server error", "request_id": request_id},
                )
                response.headers[REQUEST_ID_HEADER] = request_id
                return response
            elapsed = (time.perf_counter() - started) * 1000
            level: int = (
                logging.ERROR
                if response.status_code >= 500
                else logging.WARNING if response.status_code >= 400 else logging.INFO
            )
            logger.log(
                level,
                "%s %s -> %d (%.1f ms)",
                request.method,
                target,
                response.status_code,
                elapsed,
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_var.reset(token)
