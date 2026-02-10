from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Custom handler for HTTPException that modifies the response format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "success": False,
            "data": None,
            "message": exc.detail,
            "error": {
                "code": exc.status_code,
                "path": str(request.url.path),
            },
        },
    )
