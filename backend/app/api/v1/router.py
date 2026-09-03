from fastapi import APIRouter

from app.api.v1.routers import ai, appointments, auth, checkup_advisor, consent, documents, families, invites, lab_bookings, members, otp, prescriptions, profiles, providers, search, teleconsult, transfers, vitals, visibility

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
api_router.include_router(appointments.router)
api_router.include_router(consent.router)
api_router.include_router(teleconsult.router)
api_router.include_router(prescriptions.router)
api_router.include_router(lab_bookings.router)
api_router.include_router(checkup_advisor.router)
api_router.include_router(vitals.router)
