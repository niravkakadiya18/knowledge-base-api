from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def get_first_error_message(exc: RequestValidationError):
    if exc.errors():
        first_error = exc.errors()[0]
        field = first_error["loc"][-1] if first_error["loc"] else "unknown field"
        error_type = first_error["type"]

        if error_type == "missing":
            return f"{field} field required"
        else:
            return f"{field} field {first_error['msg']}"
    return "Validation error"


async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "success": False,
            "data": None,
            "message": get_first_error_message(exc),
            "error": {
                "details": jsonable_encoder(exc.errors())
            }
        },
    )
