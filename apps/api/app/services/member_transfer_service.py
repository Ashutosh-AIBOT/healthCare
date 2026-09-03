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
                MemberTransfer.status.in_((TransferStatus.PENDING, TransferStatus.APPROVED)),
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
        """Dual consent: both from_family and to_family must confirm before COMPLETED."""
        transfer = await db.get(MemberTransfer, transfer_id)
        if transfer is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Transfer not found.")
        if transfer.status not in (TransferStatus.PENDING, TransferStatus.APPROVED):
            raise AppError(code="TRANSFER_INVALID", status=400, detail="Transfer is not pending.")

        user = await db.get(User, confirmed_by_user_id)
        if user is None or user.family_id is None:
            raise AppError(code="FORBIDDEN", status=403, detail="Confirmer must belong to a family.")

        if user.family_id == transfer.from_family_id:
            transfer.from_family_confirmed_by = confirmed_by_user_id
        elif user.family_id == transfer.to_family_id:
            transfer.to_family_confirmed_by = confirmed_by_user_id
        else:
            raise AppError(
                code="TRANSFER_FORBIDDEN",
                status=403,
                detail="Only members of the source or target family may confirm.",
            )

        # Keep legacy column as last confirmer for compatibility.
        transfer.confirmed_by_user_id = confirmed_by_user_id

        both_confirmed = (
            transfer.from_family_confirmed_by is not None and transfer.to_family_confirmed_by is not None
        )
        if both_confirmed:
            member = await db.get(FamilyMember, transfer.member_id)
            if member is None:
                raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
            member.family_id = transfer.to_family_id
            transfer.status = TransferStatus.COMPLETED
            transfer.completed_at = datetime.now(UTC)
        else:
            transfer.status = TransferStatus.APPROVED

        await db.flush()
        return MemberTransferOut.model_validate(transfer)


member_transfer_service = MemberTransferService()
