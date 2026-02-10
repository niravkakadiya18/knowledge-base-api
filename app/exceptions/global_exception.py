# app/exceptions/global_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status

from app.config.logger import logger


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches any unhandled exceptions globally.
    Logs details and returns a safe JSON response.
    """
    logger.exception(
        f"Unhandled error during request: {request.url.path} - Error: {str(exc)}"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "success": False,
            "data": None,
            "message": "Something went wrong. Please try again later.",
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "path": str(request.url.path),
            },
        },
    )
