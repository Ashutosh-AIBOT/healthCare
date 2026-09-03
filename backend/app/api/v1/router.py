from fastapi import APIRouter

from app.api.v1.routers import ai, auth, documents, families, invites, members, otp, profiles, providers, transfers, visibility

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(otp.router)
api_router.include_router(families.router)
api_router.include_router(members.router)
api_router.include_router(invites.router)
api_router.include_router(transfers.router)
api_router.include_router(visibility.router)
api_router.include_router(profiles.router)
api_router.include_router(providers.router)
api_router.include_router(documents.router)
api_router.include_router(ai.router)
