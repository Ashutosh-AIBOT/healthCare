import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.member_transfer import MemberTransfer, TransferStatus
from app.models.user import User
from app.schemas.member_transfer import MemberTransferOut


class MemberTransferService:
    async def request(self, db: AsyncSession, member_id: uuid.UUID, to_family_id: uuid.UUID, requested_by_user_id: uuid.UUID) -> MemberTransferOut:
        member = await db.get(FamilyMember, member_id)
        if member is None or member.deleted_at is not None:
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

        from_family_id = member.family_id
        if from_family_id == to_family_id:
            raise AppError(code="TRANSFER_SAME_FAMILY", status=400, detail="Source and target family are the same.")

        to_family = await db.get(Family, to_family_id)
        if to_family is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Target family not found.")

        existing = await db.scalar(
            select(MemberTransfer).where(
                MemberTransfer.member_id == member_id,
                MemberTransfer.status == TransferStatus.PENDING,
            )
        )
        if existing:
            raise AppError(code="TRANSFER_PENDING", status=409, detail="A transfer for this member is already pending.")

        transfer = MemberTransfer(
            member_id=member_id,
            from_family_id=from_family_id,
            to_family_id=to_family_id,
            status=TransferStatus.PENDING,
            requested_by_user_id=requested_by_user_id,
        )
        db.add(transfer)
        await db.flush()
        return MemberTransferOut.model_validate(transfer)

    async def approve(self, db: AsyncSession, transfer_id: uuid.UUID, confirmed_by_user_id: uuid.UUID) -> MemberTransferOut:
        transfer = await db.get(MemberTransfer, transfer_id)
        if transfer is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Transfer not found.")
        if transfer.status != TransferStatus.PENDING:
            raise AppError(code="TRANSFER_INVALID", status=400, detail="Transfer is not pending.")

        member = await db.get(FamilyMember, transfer.member_id)
        if member is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")

        member.family_id = transfer.to_family_id
        transfer.status = TransferStatus.COMPLETED
        transfer.confirmed_by_user_id = confirmed_by_user_id
        transfer.completed_at = datetime.now(UTC)
        await db.flush()
        return MemberTransferOut.model_validate(transfer)


member_transfer_service = MemberTransferService()
