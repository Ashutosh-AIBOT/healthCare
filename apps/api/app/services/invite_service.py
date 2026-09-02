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
from app.schemas.invite import InviteCreate, InviteOut


class InviteService:
    @staticmethod
    def _generate_token() -> str:
        return uuid.uuid4().hex + uuid.uuid4().hex

    async def create(self, db: AsyncSession, family_id: uuid.UUID, payload: InviteCreate) -> InviteOut:
        family = await db.get(Family, family_id)
        if family is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Family not found.")

        existing = await db.scalar(select(Invite).where(Invite.family_id == family_id, Invite.email == payload.email.lower(), Invite.status == InviteStatus.PENDING))
        if existing:
            raise AppError(code="INVITE_EXISTS", status=409, detail="An invite for this email already exists.")

        token = self._generate_token()
        expires_at = datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        invite = Invite(
            family_id=family_id,
            email=payload.email.lower(),
            role=payload.role,
            relation=payload.relation,
            token=token,
            status=InviteStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(invite)
        await db.flush()
        return InviteOut.model_validate(invite)

    async def accept(self, db: AsyncSession, token: str, user_id: uuid.UUID) -> InviteOut:
        invite = await db.scalar(select(Invite).where(Invite.token == token))
        if invite is None:
            raise AppError(code="INVITE_NOT_FOUND", status=404, detail="Invite not found.")
        if invite.status != InviteStatus.PENDING:
            raise AppError(code="INVITE_INVALID", status=400, detail="Invite is no longer valid.")
        if invite.expires_at < datetime.now(UTC):
            invite.status = InviteStatus.EXPIRED
            await db.flush()
            raise AppError(code="INVITE_EXPIRED", status=400, detail="Invite has expired.")

        user = await db.get(User, user_id)
        if user is None:
            raise AppError(code="NOT_FOUND", status=404, detail="User not found.")

        member = FamilyMember(
            family_id=invite.family_id,
            user_id=user_id,
            relation=invite.relation,
            is_dependent=False,
            timezone="Asia/Kolkata",
        )
        db.add(member)

        invite.status = InviteStatus.ACCEPTED
        invite.accepted_by_user_id = user_id
        invite.accepted_at = datetime.now(UTC)

        if user.family_id is None:
            user.family_id = invite.family_id

        await db.flush()
        return InviteOut.model_validate(invite)

    async def list_family_invites(self, db: AsyncSession, family_id: uuid.UUID) -> list[InviteOut]:
        result = await db.execute(select(Invite).where(Invite.family_id == family_id))
        invites = result.scalars().all()
        return [InviteOut.model_validate(i) for i in invites]

    async def revoke(self, db: AsyncSession, invite_id: uuid.UUID) -> None:
        invite = await db.get(Invite, invite_id)
        if invite is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Invite not found.")
        invite.status = InviteStatus.REVOKED
        await db.flush()


invite_service = InviteService()
