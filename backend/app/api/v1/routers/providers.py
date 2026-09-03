from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.provider import (
    DoctorAvailabilityCreate,
    DoctorAvailabilityOut,
    DoctorAvailabilityUpdate,
    DoctorDetailCreate,
    DoctorDetailUpdate,
    LabDetailCreate,
    LabDetailUpdate,
    ProviderClaimCreate,
    ProviderClaimOut,
    ProviderProfileCreate,
    ProviderProfileOut,
    ProviderProfileUpdate,
)
from app.services.provider_service import provider_service

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("/profile", status_code=201)
async def create_profile(
    payload: ProviderProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderProfileOut:
    profile = await provider_service.create_profile(db, current_user.id, payload)
    return ProviderProfileOut.model_validate(profile)


@router.get("/me")
async def get_my_profile(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderProfileOut | None:
    profile = await provider_service.get_profile_by_user(db, current_user.id)
    if profile is None:
        return None
    return ProviderProfileOut.model_validate(profile)


@router.patch("/me")
async def update_my_profile(
    payload: ProviderProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderProfileOut | None:
    profile = await provider_service.update_profile(db, current_user.id, payload)
    if profile is None:
        raise AppError(code="PROVIDER_PROFILE_NOT_FOUND", status=404, detail="Provider profile not found.")
    return ProviderProfileOut.model_validate(profile)


@router.get("/{slug}")
async def get_public_profile(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderProfileOut:
    profile = await provider_service.get_profile_by_slug(db, slug)
    if profile is None or not profile.is_active:
        raise AppError(code="PROVIDER_PROFILE_NOT_FOUND", status=404, detail="Provider profile not found.")
    return ProviderProfileOut.model_validate(profile)


@router.get("/")
async def list_profiles(
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_type: str | None = None,
) -> list[ProviderProfileOut]:
    profiles = await provider_service.list_profiles(db, provider_type)
    return [ProviderProfileOut.model_validate(profile) for profile in profiles]


@router.post("/me/doctor-details", status_code=201)
async def upsert_doctor_details(
    payload: DoctorDetailCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    profile = await provider_service.get_profile_by_user(db, current_user.id)
    if profile is None or profile.provider_type != "doctor":
        raise AppError(code="PROVIDER_PROFILE_REQUIRED", status=404, detail="Doctor profile not found.")
    detail = profile.doctor_details
    if detail is None:
        from app.models.provider import DoctorDetail
        detail = DoctorDetail(provider_profile_id=profile.id, **payload.model_dump())
        db.add(detail)
        await db.flush()
    else:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(detail, field, value)
        await db.flush()
    return {"ok": True}


@router.patch("/me/doctor-details")
async def patch_doctor_details(
    payload: DoctorDetailUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    detail = await provider_service.update_doctor_details(db, current_user.id, payload)
    if detail is None:
        raise AppError(code="DOCTOR_DETAILS_NOT_FOUND", status=404, detail="Doctor details not found.")
    return {"ok": True}


@router.post("/me/lab-details", status_code=201)
async def upsert_lab_details(
    payload: LabDetailCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    profile = await provider_service.get_profile_by_user(db, current_user.id)
    if profile is None or profile.provider_type != "lab":
        raise AppError(code="PROVIDER_PROFILE_REQUIRED", status=404, detail="Lab profile not found.")
    detail = profile.lab_details
    if detail is None:
        from app.models.provider import LabDetail
        detail = LabDetail(provider_profile_id=profile.id, **payload.model_dump())
        db.add(detail)
        await db.flush()
    else:
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(detail, field, value)
        await db.flush()
    return {"ok": True}


@router.patch("/me/lab-details")
async def patch_lab_details(
    payload: LabDetailUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    detail = await provider_service.update_lab_details(db, current_user.id, payload)
    if detail is None:
        raise AppError(code="LAB_DETAILS_NOT_FOUND", status=404, detail="Lab details not found.")
    return {"ok": True}


@router.post("/claims", status_code=201)
async def create_claim(
    payload: ProviderClaimCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderClaimOut:
    claim = await provider_service.create_claim(db, current_user.id, payload)
    return ProviderClaimOut.model_validate(claim)


@router.get("/claims")
async def list_claims(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status: str | None = None,
) -> list[ProviderClaimOut]:
    if current_user.role != "platform_admin" and current_user.role != "support_agent":
        raise AppError(code="FORBIDDEN", status=403, detail="Admin access required.")
    claims = await provider_service.list_claims(db, status)
    return [ProviderClaimOut.model_validate(claim) for claim in claims]


@router.post("/claims/{claim_id}/review")
async def review_claim(
    claim_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    approved: bool,
    reason: str | None = None,
) -> ProviderClaimOut:
    if current_user.role != "platform_admin" and current_user.role != "support_agent":
        raise AppError(code="FORBIDDEN", status=403, detail="Admin access required.")
    claim = await provider_service.review_claim(db, claim_id, current_user.id, approved, reason)
    if claim is None:
        raise AppError(code="CLAIM_NOT_FOUND", status=404, detail="Claim not found or not pending.")
    return ProviderClaimOut.model_validate(claim)


@router.post("/me/availability", status_code=201)
async def create_availability(
    payload: DoctorAvailabilityCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DoctorAvailabilityOut:
    slot = await provider_service.create_availability(db, current_user.id, payload)
    return DoctorAvailabilityOut.model_validate(slot)


@router.get("/me/availability")
async def list_my_availability(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DoctorAvailabilityOut]:
    slots = await provider_service.list_availability(db, current_user.id)
    return [DoctorAvailabilityOut.model_validate(slot) for slot in slots]


@router.patch("/me/availability/{slot_id}")
async def update_availability(
    slot_id: str,
    payload: DoctorAvailabilityUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DoctorAvailabilityOut | None:
    slot = await provider_service.update_availability(db, current_user.id, slot_id, payload)
    if slot is None:
        raise AppError(code="AVAILABILITY_NOT_FOUND", status=404, detail="Availability slot not found.")
    return DoctorAvailabilityOut.model_validate(slot)


@router.delete("/me/availability/{slot_id}")
async def delete_availability(
    slot_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    ok = await provider_service.delete_availability(db, current_user.id, slot_id)
    if not ok:
        raise AppError(code="AVAILABILITY_NOT_FOUND", status=404, detail="Availability slot not found.")
    return {"ok": True}
