# API key authentication and rate limiting

"""
API security: API key authentication and rate limiting
"""

from fastapi import Header, HTTPException, status, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitedExceeded

from config import settings

# API key authentication

async def verify_api_key(api_key: str = Header(alias="x-api-key")) -> None:
    if api_key != settings.api_key:
        raise HTTPException(
            status_code = status.HTTP__401_UNAUTHORIZED,
            detail = "Invalid or missing API key.",
        )

# Rate limiting

limiter = Limiter(key_func=get_remote_address)

async def rate_limit_exceeded_handler(request: Request, exc:RateLimitedExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )