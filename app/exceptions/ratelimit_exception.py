from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """
    Build a simple JSON response that includes the details of the rate limit
    that was hit. If no limit is hit, the countdown is added to headers.
    """
    content = {
        "status": "error",
        "success": False,
        "data": None,
        "message": f"Rate limit exceeded: {exc.detail}",
        "error": {
            "code": 429,
            "path": str(request.url.path),
        }
    }
    response = JSONResponse(
        content=content,
        status_code=429,
    )
    response = request.app.state.limiter._inject_headers(
        response, request.state.view_rate_limit
    )
    return response
