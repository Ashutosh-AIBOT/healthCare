from fastapi import APIRouter

from app.api.v1.routers import auth, families, invites, members, otp, transfers

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(otp.router)
api_router.include_router(families.router)
api_router.include_router(members.router)
api_router.include_router(invites.router)
api_router.include_router(transfers.router)
