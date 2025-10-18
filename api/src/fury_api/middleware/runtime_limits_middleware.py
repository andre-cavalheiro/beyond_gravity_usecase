import asyncio
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

__all__ = ["RuntimeLimitsMiddleware"]
TIMEOUT_SECONDS = 10


class RuntimeLimitsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            response = await asyncio.wait_for(call_next(request), timeout=TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            response = Response("Runtime Limit Timeout Exceeded", status_code=504)
        return response
