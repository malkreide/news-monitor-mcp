"""Middleware fuer den Streamable-HTTP-Mode.

Public surface:
    BearerAuthMiddleware       — Erzwingt Authorization: Bearer <token>
    OriginAllowlistMiddleware  — Optional, DNS-Rebinding-Schutz
    RequestIdMiddleware        — Setzt _request_id ContextVar pro Request
    _parse_allowed_origins     — CSV-Env -> frozenset
    _attach_middlewares        — Hängt Middleware-Stack in der richtigen Reihenfolge an

Behebt Audit-Finding SEC-HTTP-NO-AUTH (critical, 2026-05-13).
"""

import secrets
import time
import uuid
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from news_monitor_mcp.logging_setup import _request_id, logger


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Erzwingt Bearer-Token-Authentifizierung auf allen Requests."""

    def __init__(self, app: Any, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        auth = request.headers.get("authorization", "")
        scheme, _, presented = auth.partition(" ")
        if scheme.lower() != "bearer" or not presented:
            return JSONResponse({"error": "unauthorized"}, status_code=401,
                                headers={"www-authenticate": "Bearer"})
        if not secrets.compare_digest(presented, self._token):
            return JSONResponse({"error": "unauthorized"}, status_code=401,
                                headers={"www-authenticate": "Bearer"})
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Setzt eine Request-ID pro HTTP-Request und exponiert sie via x-request-id-Header."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if incoming else uuid.uuid4().hex[:12]
        token = _request_id.set(rid)
        t0 = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.monotonic() - t0) * 1000
            logger.info("http_request method=%s path=%s dur_ms=%.1f",
                        request.method, request.url.path, duration_ms)
            _request_id.reset(token)
        response.headers["x-request-id"] = rid
        return response


class OriginAllowlistMiddleware(BaseHTTPMiddleware):
    """Blockiert Requests mit unerwartetem Origin-Header (DNS-Rebinding-Schutz)."""

    def __init__(self, app: Any, allowed_origins: frozenset[str]) -> None:
        super().__init__(app)
        self._allowed = allowed_origins

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        origin = request.headers.get("origin")
        if origin is not None and origin not in self._allowed:
            return JSONResponse({"error": "origin not allowed"}, status_code=403)
        return await call_next(request)


def _parse_allowed_origins(raw: Optional[str]) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(o.strip() for o in raw.split(",") if o.strip())


def _attach_middlewares(app: Any, token: str, allowed_origins: frozenset[str]) -> Any:
    """Haengt den Middleware-Stack in der richtigen Reihenfolge an die Starlette-App.

    Reihenfolge im Stack (outermost first, weil Starlette LIFO mountet):
      RequestIdMiddleware → OriginAllowlistMiddleware → BearerAuthMiddleware → App.
    Die Request-ID ist damit auch bei abgewiesenen 401/403-Responses verfuegbar.
    """
    app.add_middleware(BearerAuthMiddleware, token=token)
    if allowed_origins:
        app.add_middleware(OriginAllowlistMiddleware, allowed_origins=allowed_origins)
    app.add_middleware(RequestIdMiddleware)
    return app
