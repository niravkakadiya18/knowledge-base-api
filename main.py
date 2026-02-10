import warnings

# Suppress Pydantic V1 compatibility warning on Python 3.14+
warnings.filterwarnings("ignore", category=UserWarning, module="fastapi._compat.v1")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._config")

from fastapi import FastAPI
from app.dto.api_response import APIResponse


from app.config.settings import settings
from app.exceptions import (
    HTTPException,
    RateLimitExceeded,
    RequestValidationError,
    global_exception_handler,
    http_exception_handler,
    rate_limit_exceeded_handler,
    validation_exception_handler,
)
# Routers
from app.routers import (
    users,
    auth,
    knowledge,
    stakeholders,
    templates,
    deliverables,
    clients
)


# CREATE APP
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)


@app.get("/", response_model=APIResponse[dict])
def root():
    try:
        return APIResponse(
            status="success",
            success=True,
            data=None,
            message="Knowledge Base API running"
        )
    except Exception as e:
        # Let the global handler catch it, but demonstrating try-catch placement
        raise e


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(knowledge.router)
app.include_router(stakeholders.router)
app.include_router(clients.router)
app.include_router(templates.router)
app.include_router(deliverables.router)



# Register Exception Handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore
app.add_exception_handler(Exception, global_exception_handler)  # type: ignore


if __name__ == "__main__":
    try:
        # Import uvicorn here to avoid unused import warning if running via uvicorn CLI
        import uvicorn
        # This block is executed when running `uv run main.py`
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        print(f"Error starting server: {e}")
