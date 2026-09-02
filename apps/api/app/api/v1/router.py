from fastapi import APIRouter

from app.api.v1.routers import auth, otp

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(otp.router)
