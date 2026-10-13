from fastapi import APIRouter

from app.api.v1.routers import (
    ai, auth, documents, families, fitness, invites, learn,
    members, nutrition, otp, profiles, providers, search,
    time, transfers, visibility, xomni, telegram,
)

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
api_router.include_router(search.router)
api_router.include_router(documents.router)
api_router.include_router(ai.router)
api_router.include_router(time.router)
api_router.include_router(learn.router)
api_router.include_router(xomni.router)        # Xomni chat + voice + points
api_router.include_router(telegram.router)     # Per-user Telegram bots
api_router.include_router(nutrition.router)    # BMI + meal plan
api_router.include_router(fitness.router)      # Fitness goals + activity
