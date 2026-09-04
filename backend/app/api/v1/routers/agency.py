import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.agency import Agency, AgencyMember, AgencyMemberRole, AgencyStatus
from app.models.user import User

router = APIRouter(prefix="/agencies", tags=["agency"])


@router.get("", response_model=list[dict])
async def list_agencies(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    result = await db.execute(
        select(Agency).where(Agency.status == AgencyStatus.ACTIVE).order_by(Agency.created_at.desc())
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "slug": a.slug,
            "description": a.description,
            "contact_email": a.contact_email,
        }
        for a in result.scalars().all()
    ]


@router.get("/{agency_id}", response_model=dict)
async def get_agency(
    agency_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    agency = await db.get(Agency, agency_id)
    if agency is None:
        raise AppError(code="NOT_FOUND", status=404, detail="Agency not found.")
    return {
        "id": str(agency.id),
        "name": agency.name,
        "slug": agency.slug,
        "description": agency.description,
        "contact_email": agency.contact_email,
        "contact_phone": agency.contact_phone,
        "status": agency.status,
    }


@router.post("/{agency_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_agency_member(
    agency_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    agency = await db.get(Agency, agency_id)
    if agency is None:
        raise AppError(code="NOT_FOUND", status=404, detail="Agency not found.")
    owner_check = await db.execute(
        select(AgencyMember).where(
            AgencyMember.agency_id == agency_id,
            AgencyMember.user_id == current_user.id,
            AgencyMember.role == AgencyMemberRole.OWNER,
        )
    )
    if owner_check.scalar_one_or_none() is None:
        raise AppError(code="FORBIDDEN", status=403, detail="Only owners can add members.")
    existing = await db.execute(
        select(AgencyMember).where(
            AgencyMember.agency_id == agency_id,
            AgencyMember.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(
        AgencyMember(
            agency_id=agency_id,
            user_id=user_id,
            role=AgencyMemberRole.STAFF,
        )
    )
    await db.commit()
