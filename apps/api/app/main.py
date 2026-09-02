from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.errors import AppError, app_error_handler, db_error_handler
from sqlalchemy.exc import SQLAlchemyError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title="Aarogya API", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(SQLAlchemyError, db_error_handler)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
