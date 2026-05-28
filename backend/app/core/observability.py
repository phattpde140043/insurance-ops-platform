import json
import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


TRACE_ID_HEADER = "X-Trace-Id"
logger = logging.getLogger("opsbridge.request")


def new_trace_id() -> str:
    return uuid4().hex


class TraceIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        trace_id = request.headers.get(TRACE_ID_HEADER) or new_trace_id()
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[TRACE_ID_HEADER] = trace_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "trace_id": trace_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                    separators=(",", ":"),
                )
            )
