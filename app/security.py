# API key authentication and rate limiting

"""
API security: API key authentication and rate limiting
"""

from fastapi import HTTPException, status, Request, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings

# API key authentication

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
async def verify_api_key(x_api_key: str = Security(api_key_header)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or missing API key.",
        )

# Rate limiting

limiter = Limiter(key_func=get_remote_address)

async def rate_limit_exceeded_handler(request: Request, exc:RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )