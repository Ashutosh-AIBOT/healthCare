import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.member_medical_profile import MemberMedicalProfile
from app.models.user import User
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberOut, FamilyMemberUpdate
from app.schemas.invite import InviteCreate, InviteOut
from app.schemas.member_medical_profile import (
    MemberMedicalProfileCreate,
    MemberMedicalProfileOut,
    MemberMedicalProfileUpdate,
)
from app.schemas.member_transfer import MemberTransferCreate, MemberTransferOut
from app.services.invite_service import invite_service
from app.services.member_transfer_service import member_transfer_service
from app.services.settings_service import get_int_setting
from app.services.visibility_service import visibility_service


def _member_full_payload(member: FamilyMember) -> dict:
    data = FamilyMemberOut.model_validate(member).model_dump(mode="json")
    profile: MemberMedicalProfile | None = member.medical_profile
    if profile is not None:
        data["conditions"] = profile.conditions
        data["medications"] = profile.medications
        data["allergies"] = profile.allergies
        data["notes"] = profile.notes
    return data


class FamilyService:
    def __init__(self) -> None:
        self.invite_service = invite_service
        self.transfer_service = member_transfer_service

    async def get_my_family(self, db: AsyncSession, user_id: uuid.UUID) -> Family | None:
        user = await db.get(User, user_id)
        if user is None or user.family_id is None:
            return None
        return await db.get(Family, user.family_id)

    async def create_family(self, db: AsyncSession, user_id: uuid.UUID, name: str) -> Family:
        family = Family(name=name)
        db.add(family)
        await db.flush()

        member = FamilyMember(
            family_id=family.id,
            user_id=user_id,
            relation=None,
            is_dependent=False,
            timezone="Asia/Kolkata",
        )
        db.add(member)
        await db.flush()

        user = await db.get(User, user_id)
        if user:
            user.family_id = family.id

        return family

    async def add_member(self, db: AsyncSession, family_id: uuid.UUID, payload: FamilyMemberCreate) -> FamilyMemberOut:
        from datetime import date

        from app.core.errors import AppError
        from app.services.settings_service import get_int_setting

        majority = await get_int_setting(db, "majority_age_years")
        is_dependent = payload.is_dependent
        guardian_id = payload.guardian_id

        if payload.date_of_birth is not None:
            today = date.today()
            years = (
                today.year
                - payload.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (payload.date_of_birth.month, payload.date_of_birth.day)
                )
            )
            if years < majority:
                is_dependent = True
                if guardian_id is None:
                    raise AppError(
                        code="GUARDIAN_REQUIRED",
                        status=400,
                        detail=f"Members under majority age ({majority}) require a guardian_id.",
                    )

        member = FamilyMember(
            family_id=family_id,
            user_id=payload.user_id,
            relation=payload.relation,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            blood_group=payload.blood_group,
            is_dependent=is_dependent,
            guardian_id=guardian_id,
            timezone=payload.timezone,
            diet_preference=payload.diet_preference,
        )
        db.add(member)
        await db.flush()
        return FamilyMemberOut.model_validate(member)

    async def _viewer_member_id(self, db: AsyncSession, family_id: uuid.UUID, viewer_user_id: uuid.UUID) -> uuid.UUID | None:
        result = await db.execute(
            select(FamilyMember.id).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == viewer_user_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self,
        db: AsyncSession,
        family_id: uuid.UUID,
        viewer_user_id: uuid.UUID | None = None,
    ) -> list[dict]:
        result = await db.execute(
            select(FamilyMember)
            .where(FamilyMember.family_id == family_id, FamilyMember.deleted_at.is_(None))
            .options(selectinload(FamilyMember.medical_profile))
        )
        members = list(result.scalars().all())
        viewer_member_id = None
        if viewer_user_id is not None:
            viewer_member_id = await self._viewer_member_id(db, family_id, viewer_user_id)

        out: list[dict] = []
        for member in members:
            full = _member_full_payload(member)
            is_self = viewer_user_id is not None and member.user_id == viewer_user_id
            if is_self or viewer_member_id is None:
                out.append(full)
                continue
            if member.id == viewer_member_id:
                out.append(full)
                continue
            granted = await visibility_service.get_grant_levels(db, member.id, viewer_member_id)
            filtered = visibility_service.filter_member_payload(full, granted)
            if viewer_user_id is not None:
                for key in ("conditions", "medications", "allergies", "notes"):
                    if key in filtered:
                        field_key = "medications" if key in ("medications", "allergies") else "conditions"
                        await visibility_service.log_access(
                            db, member.id, viewer_user_id, field_key, purpose="family_list"
                        )
            out.append(filtered)
        return out

    async def get_member(
        self,
        db: AsyncSession,
        member_id: uuid.UUID,
        viewer_user_id: uuid.UUID | None = None,
    ) -> dict | None:
        result = await db.execute(
            select(FamilyMember)
            .where(FamilyMember.id == member_id, FamilyMember.deleted_at.is_(None))
            .options(selectinload(FamilyMember.medical_profile))
        )
        member = result.scalar_one_or_none()
        if member is None:
            return None
        full = _member_full_payload(member)
        if viewer_user_id is None or member.user_id == viewer_user_id:
            return full
        viewer_member_id = await self._viewer_member_id(db, member.family_id, viewer_user_id)
        if viewer_member_id is None or viewer_member_id == member.id:
            return full
        granted = await visibility_service.get_grant_levels(db, member.id, viewer_member_id)
        filtered = visibility_service.filter_member_payload(full, granted)
        for key in ("conditions", "medications", "allergies", "notes"):
            if key in filtered and viewer_user_id is not None:
                field_key = "medications" if key in ("medications", "allergies") else "conditions"
                await visibility_service.log_access(
                    db, member.id, viewer_user_id, field_key, purpose="family_read"
                )
        return filtered

    async def update_member(self, db: AsyncSession, member_id: uuid.UUID, payload: FamilyMemberUpdate) -> FamilyMemberOut | None:
        member = await db.get(FamilyMember, member_id)
        if member is None or member.deleted_at is not None:
            return None
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(member, field, value)
        await db.flush()
        return FamilyMemberOut.model_validate(member)

    async def invite_member(self, db: AsyncSession, family_id: uuid.UUID, payload: InviteCreate) -> InviteOut:
        return await self.invite_service.create(db, family_id, payload)

    async def accept_invite(self, db: AsyncSession, token: str, user_id: uuid.UUID) -> InviteOut:
        return await self.invite_service.accept(db, token, user_id)

    async def request_transfer(self, db: AsyncSession, member_id: uuid.UUID, payload: MemberTransferCreate, requested_by_user_id: uuid.UUID) -> MemberTransferOut:
        return await self.transfer_service.request(db, member_id, payload.to_family_id, requested_by_user_id)

    async def approve_transfer(self, db: AsyncSession, transfer_id: uuid.UUID, confirmed_by_user_id: uuid.UUID) -> MemberTransferOut:
        return await self.transfer_service.approve(db, transfer_id, confirmed_by_user_id)


family_service = FamilyService()
