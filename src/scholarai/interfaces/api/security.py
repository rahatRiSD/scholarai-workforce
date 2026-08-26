"""API authentication: bearer API keys, constant-time comparison.

With no keys configured the API serves anyone — convenient for `scholarai
serve` on a laptop — but logs a loud warning per request rather than
silently, and ``Settings`` refuses to boot in production without keys (see
``infrastructure.config.settings``), so the convenient mode can't reach
production by accident. This mirrors the reference trading platform's
``interfaces/api/security.py`` design.
"""

from __future__ import annotations

import hmac
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from scholarai.infrastructure.observability import get_logger

log = get_logger(__name__)
_bearer = HTTPBearer(auto_error=False, description="API key as a bearer token")


def _configured_keys(request: Request) -> tuple[str, ...]:
    return cast(tuple[str, ...], request.app.state.container.settings.api.api_keys)


def _matches_any(candidate: str, keys: tuple[str, ...]) -> bool:
    matched = False
    for key in keys:
        if hmac.compare_digest(candidate, key):
            matched = True
    return matched


async def authenticate(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> str:
    keys = _configured_keys(request)
    if not keys:
        log.warning("api.unauthenticated_request", path=request.url.path)
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _matches_any(credentials.credentials, keys):
        log.warning("api.invalid_credentials", path=request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return "authenticated"


RequiresAuth = Depends(authenticate)
