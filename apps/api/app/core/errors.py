from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, OperationalError


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        status: int,
        detail: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status = status
        self.detail = detail
        self.meta = meta or {}
        super().__init__(detail)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={
            "type": f"https://aarogya.app/errors/{exc.code.lower().replace('_', '-')}",
            "title": exc.code.replace("_", " ").title(),
            "status": exc.status,
            "code": exc.code,
            "detail": exc.detail,
            "meta": exc.meta,
        },
    )

async def db_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    if isinstance(exc, OperationalError):
        code = "DB_UNAVAILABLE"
        status = 503
        detail = "Database is temporarily unavailable. Please retry."
    else:
        code = "DB_ERROR"
        status = 500
        detail = f"A database error occurred: {exc!r}"
    return JSONResponse(
        status_code=status,
        content={
            "type": f"https://aarogya.app/errors/{code.lower()}",
            "title": code.replace("_", " ").title(),
            "status": status,
            "code": code,
            "detail": detail,
            "meta": {},
        },
    )
