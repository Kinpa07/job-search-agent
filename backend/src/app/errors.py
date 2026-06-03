from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger()


def _envelope(
    error_type: str, message: str, details: Sequence[Any] | None = None
) -> dict[str, Any]:
    return {"error": {"type": error_type, "message": message, "details": list(details or [])}}


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_envelope("validation_error", "Request validation failed", exc.errors()),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Derive a readable type slug from the status code (404 -> "not_found").
    try:
        error_type = HTTPStatus(exc.status_code).name.lower()
    except ValueError:
        error_type = "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=_envelope(error_type, str(exc.detail)),
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log the full traceback server-side; never leak internals to the client.
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content=_envelope("internal_error", "Internal server error"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
