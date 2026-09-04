from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import ConsentDocument, User
from app.schemas.consent import (
    ConsentAccept,
    ConsentDocumentOut,
    ConsentOut,
    ConsentRevoke,
)
from app.services.consent_service import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/documents", response_model=list[ConsentDocumentOut])
async def list_consent_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConsentDocumentOut]:
    """Public, cacheable: current active version of each consent document."""
    docs = await consent_service.get_active_consent_documents(db)
    return [ConsentDocumentOut.model_validate(d) for d in docs]


@router.post("/accept", response_model=ConsentOut, status_code=201)
async def accept_consent(
    payload: ConsentAccept,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConsentOut:
    """Record explicit consent acceptance. user_id comes from the JWT."""
    consent = await consent_service.record_consent(
        db,
        user_id=current_user.id,
        consent_type=payload.consent_type,
        version=payload.version,
    )
    return ConsentOut.model_validate(consent)


@router.get("/my-consents", response_model=list[ConsentOut])
async def my_consents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ConsentOut]:
    """List all consents (active and revoked) belonging to the caller."""
    rows = await consent_service.get_consents(db, current_user.id)
    return [ConsentOut.model_validate(r) for r in rows]


@router.post("/revoke", response_model=ConsentOut | None)
async def revoke_consent(
    payload: ConsentRevoke,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConsentOut | None:
    """Revoke the caller's active consent for the given type. Returns null if none."""
    consent = await consent_service.revoke_consent(
        db,
        user_id=current_user.id,
        consent_type=payload.consent_type,
    )
    if consent is None:
        return None
    return ConsentOut.model_validate(consent)
