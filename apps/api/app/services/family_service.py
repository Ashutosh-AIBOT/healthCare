import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.invite import Invite, InviteStatus
from app.models.user import User
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberOut
from app.schemas.invite import InviteCreate, InviteOut
from app.schemas.member_transfer import MemberTransferCreate, MemberTransferOut
from app.services.member_transfer_service import MemberTransferService, member_transfer_service
from app.services.invite_service import InviteService, invite_service


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
        member = FamilyMember(
            family_id=family_id,
            user_id=payload.user_id,
            relation=payload.relation,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender,
            blood_group=payload.blood_group,
            is_dependent=payload.is_dependent,
            guardian_id=payload.guardian_id,
            timezone=payload.timezone,
            diet_preference=payload.diet_preference,
        )
        db.add(member)
        await db.flush()
        return FamilyMemberOut.model_validate(member)

    async def list_members(self, db: AsyncSession, family_id: uuid.UUID) -> list[FamilyMemberOut]:
        result = await db.execute(select(FamilyMember).where(FamilyMember.family_id == family_id, FamilyMember.deleted_at.is_(None)))
        members = result.scalars().all()
        return [FamilyMemberOut.model_validate(m) for m in members]

    async def get_member(self, db: AsyncSession, member_id: uuid.UUID) -> FamilyMemberOut | None:
        member = await db.get(FamilyMember, member_id)
        if member is None or member.deleted_at is not None:
            return None
        return FamilyMemberOut.model_validate(member)

    async def update_member(self, db: AsyncSession, member_id: uuid.UUID, payload: FamilyMemberCreate) -> FamilyMemberOut | None:
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
