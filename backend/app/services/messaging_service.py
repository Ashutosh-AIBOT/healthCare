"""Module 10: messaging, invitations, notifications service.

Rules honoured:
- PHI never enters notification payloads (rule 7). Push payloads carry only
  conversation_id, sender_user_id, kind, created_at.
- Invitations default to 14-day expiry (configurable via ttl_days).
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.session import set_user_context
from app.models.messaging import (
    Conversation,
    ConversationParticipant,
    ConversationType,
    Invitation,
    InvitationStatus,
    InvitationType,
    Message,
    MessageTier,
    Notification,
    NotificationType,
)
from app.models.user import User
from app.schemas.messaging import (
    ConversationCreate,
    ConversationOut,
    InvitationCreate,
    InvitationOut,
    MessageCreate,
    MessageOut,
)


class _NotificationHub:
    """In-memory pub/sub for the MVP. Drop-in replace with Redis pub/sub later."""

    def __init__(self) -> None:
        self._subs: dict[uuid.UUID, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: uuid.UUID) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subs[user_id].add(q)
        return q

    async def unsubscribe(self, user_id: uuid.UUID, q: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subs[user_id].discard(q)
            if not self._subs[user_id]:
                self._subs.pop(user_id, None)

    async def publish(self, user_id: uuid.UUID, event: dict[str, Any]) -> None:
        async with self._lock:
            queues = list(self._subs.get(user_id, ()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


notification_hub = _NotificationHub()


class MessagingService:
    DEFAULT_TTL_DAYS = 14
    MAX_TTL_DAYS = 90

    # ----- Conversations -----
    async def create_conversation(
        self, db: AsyncSession, *, creator_user_id: uuid.UUID, payload: ConversationCreate
    ) -> ConversationOut:
        ids = {creator_user_id, *payload.participant_user_ids}
        if not ids:
            raise AppError(code="CONVERSATION_EMPTY", status=400, detail="At least one participant required.")

        await set_user_context(db, creator_user_id)

        existing_users = (await db.scalars(select(User.id).where(User.id.in_(ids)))).all()
        if len(existing_users) != len(ids):
            raise AppError(code="USER_NOT_FOUND", status=404, detail="One or more participants not found.")

        conv = Conversation(type=payload.type)
        db.add(conv)
        await db.flush()

        for uid in ids:
            db.add(ConversationParticipant(conversation_id=conv.id, user_id=uid))
        await db.flush()

        await self._broadcast_to_participants(
            db,
            participants=list(ids),
            event={
                "kind": "conversation.created",
                "conversation_id": str(conv.id),
                "type": conv.type,
            },
        )

        return ConversationOut(
            id=conv.id,
            type=conv.type,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            participant_user_ids=sorted(ids),
        )

    async def get_conversation(
        self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> ConversationOut:
        await set_user_context(db, user_id)
        conv = await db.get(Conversation, conversation_id)
        if conv is None:
            raise AppError(code="CONVERSATION_NOT_FOUND", status=404, detail="Conversation not found.")

        participant = await db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        if participant is None:
            raise AppError(code="FORBIDDEN", status=403, detail="Not a participant.")

        participants = (
            await db.scalars(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id == conversation_id
                )
            )
        ).all()

        return ConversationOut(
            id=conv.id,
            type=conv.type,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            participant_user_ids=sorted(participants),
        )

    async def list_conversations(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[ConversationOut]:
        await set_user_context(db, user_id)

        rows = (
            await db.execute(
                select(Conversation, ConversationParticipant.user_id)
                .join(ConversationParticipant, ConversationParticipant.conversation_id == Conversation.id)
                .where(ConversationParticipant.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
            )
        ).all()

        result: dict[uuid.UUID, Conversation] = {}
        for conv, _uid in rows:
            result[conv.id] = conv

        if not result:
            return []

        participants_by_conv: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        part_rows = (
            await db.execute(
                select(ConversationParticipant.conversation_id, ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id.in_(result.keys())
                )
            )
        ).all()
        for cid, uid in part_rows:
            participants_by_conv[cid].append(uid)

        return [
            ConversationOut(
                id=c.id,
                type=c.type,
                created_at=c.created_at,
                updated_at=c.updated_at,
                participant_user_ids=sorted(participants_by_conv.get(c.id, [])),
            )
            for c in result.values()
        ]

    async def assert_participant(
        self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await set_user_context(db, user_id)
        row = await db.scalar(
            select(ConversationParticipant).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        if row is None:
            raise AppError(code="FORBIDDEN", status=403, detail="Not a participant.")

    async def send_message(
        self,
        db: AsyncSession,
        *,
        conversation_id: uuid.UUID,
        sender_user_id: uuid.UUID,
        payload: MessageCreate,
    ) -> MessageOut:
        await set_user_context(db, sender_user_id)
        await self.assert_participant(db, conversation_id, sender_user_id)

        msg = Message(
            conversation_id=conversation_id,
            sender_user_id=sender_user_id,
            content=payload.content,
            tier=payload.tier,
        )
        db.add(msg)
        await db.flush()

        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )

        other_participants = (
            await db.scalars(
                select(ConversationParticipant.user_id).where(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id != sender_user_id,
                )
            )
        ).all()

        for uid in other_participants:
            await self._push_notification(
                db,
                user_id=uid,
                kind="message.received",
                payload={
                    "conversation_id": str(conversation_id),
                    "message_id": str(msg.id),
                    "sender_user_id": str(sender_user_id),
                    "tier": payload.tier,
                },
            )

        return MessageOut(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_user_id=msg.sender_user_id,
            content=msg.content,
            tier=msg.tier,
            created_at=msg.created_at,
        )

    async def list_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[MessageOut]:
        limit = max(1, min(limit, 200))
        await set_user_context(db, user_id)
        await self.assert_participant(db, conversation_id, user_id)

        rows = (
            await db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
        ).all()
        rows = list(reversed(rows))
        return [
            MessageOut(
                id=m.id,
                conversation_id=m.conversation_id,
                sender_user_id=m.sender_user_id,
                content=m.content,
                tier=m.tier,
                created_at=m.created_at,
            )
            for m in rows
        ]

    # ----- Invitations -----
    async def create_invitation(
        self,
        db: AsyncSession,
        *,
        from_user_id: uuid.UUID,
        payload: InvitationCreate,
        ttl_days: int | None = None,
    ) -> InvitationOut:
        if payload.to_user_id is None and payload.to_email is None:
            raise AppError(code="INVITATION_TARGET_REQUIRED", status=400, detail="to_user_id or to_email required.")

        ttl = ttl_days if ttl_days is not None else self.DEFAULT_TTL_DAYS
        if ttl <= 0 or ttl > self.MAX_TTL_DAYS:
            raise AppError(code="INVITATION_TTL_INVALID", status=400, detail=f"ttl must be 1..{self.MAX_TTL_DAYS} days.")

        await set_user_context(db, from_user_id)

        if payload.to_user_id is not None:
            existing = await db.scalar(
                select(Invitation).where(
                    and_(
                        Invitation.from_user_id == from_user_id,
                        Invitation.to_user_id == payload.to_user_id,
                        Invitation.status == InvitationStatus.PENDING,
                    )
                )
            )
            if existing:
                raise AppError(code="INVITATION_EXISTS", status=409, detail="Pending invitation already exists.")

        invite = Invitation(
            from_user_id=from_user_id,
            to_user_id=payload.to_user_id,
            to_email=str(payload.to_email) if payload.to_email else None,
            type=payload.type,
            payload=payload.payload or {},
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=ttl),
        )
        db.add(invite)
        await db.flush()

        if payload.to_user_id is not None:
            await self._push_notification(
                db,
                user_id=payload.to_user_id,
                kind="invitation.received",
                payload={
                    "invitation_id": str(invite.id),
                    "from_user_id": str(from_user_id),
                    "type": invite.type,
                },
            )

        return self._invitation_to_out(invite)

    async def accept_invitation(
        self, db: AsyncSession, invitation_id: uuid.UUID, user_id: uuid.UUID
    ) -> InvitationOut:
        await set_user_context(db, user_id)
        invite = await db.get(Invitation, invitation_id)
        if invite is None:
            raise AppError(code="INVITATION_NOT_FOUND", status=404, detail="Invitation not found.")

        if invite.to_user_id is not None and invite.to_user_id != user_id:
            raise AppError(code="FORBIDDEN", status=403, detail="Invitation not addressed to this user.")

        if invite.status != InvitationStatus.PENDING:
            raise AppError(code="INVITATION_INVALID", status=400, detail="Invitation is no longer pending.")

        if invite.expires_at < datetime.now(UTC):
            invite.status = InvitationStatus.EXPIRED
            invite.responded_at = datetime.now(UTC)
            await db.flush()
            raise AppError(code="INVITATION_EXPIRED", status=400, detail="Invitation has expired.")

        invite.status = InvitationStatus.ACCEPTED
        invite.to_user_id = user_id
        invite.responded_at = datetime.now(UTC)

        conv = Conversation(type=_conversation_type_from_invitation(invite.type))
        db.add(conv)
        await db.flush()
        db.add(ConversationParticipant(conversation_id=conv.id, user_id=invite.from_user_id))
        db.add(ConversationParticipant(conversation_id=conv.id, user_id=user_id))

        await db.flush()

        await self._broadcast_to_participants(
            db,
            participants=[invite.from_user_id, user_id],
            event={
                "kind": "invitation.accepted",
                "invitation_id": str(invite.id),
                "conversation_id": str(conv.id),
            },
        )

        return self._invitation_to_out(invite)

    async def decline_invitation(
        self, db: AsyncSession, invitation_id: uuid.UUID, user_id: uuid.UUID
    ) -> InvitationOut:
        await set_user_context(db, user_id)
        invite = await db.get(Invitation, invitation_id)
        if invite is None:
            raise AppError(code="INVITATION_NOT_FOUND", status=404, detail="Invitation not found.")

        if invite.to_user_id is not None and invite.to_user_id != user_id:
            raise AppError(code="FORBIDDEN", status=403, detail="Invitation not addressed to this user.")

        if invite.status != InvitationStatus.PENDING:
            raise AppError(code="INVITATION_INVALID", status=400, detail="Invitation is no longer pending.")

        invite.status = InvitationStatus.DECLINED
        invite.to_user_id = user_id
        invite.responded_at = datetime.now(UTC)

        await self._push_notification(
            db,
            user_id=invite.from_user_id,
            kind="invitation.declined",
            payload={
                "invitation_id": str(invite.id),
                "to_user_id": str(user_id),
            },
        )

        return self._invitation_to_out(invite)

    async def list_pending_invitations(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[InvitationOut]:
        await set_user_context(db, user_id)
        rows = (
            await db.scalars(
                select(Invitation).where(
                    or_(
                        Invitation.to_user_id == user_id,
                        Invitation.from_user_id == user_id,
                    ),
                    Invitation.status == InvitationStatus.PENDING,
                ).order_by(Invitation.created_at.desc())
            )
        ).all()
        return [self._invitation_to_out(i) for i in rows]

    async def list_invitations(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[InvitationOut]:
        await set_user_context(db, user_id)
        rows = (
            await db.scalars(
                select(Invitation).where(
                    or_(
                        Invitation.to_user_id == user_id,
                        Invitation.from_user_id == user_id,
                    ),
                ).order_by(Invitation.created_at.desc())
            )
        ).all()
        return [self._invitation_to_out(i) for i in rows]

    async def sweep_expired_invitations(self, db: AsyncSession) -> int:
        now = datetime.now(UTC)
        result = await db.execute(
            update(Invitation)
            .where(
                Invitation.status == InvitationStatus.PENDING,
                Invitation.expires_at < now,
            )
            .values(status=InvitationStatus.EXPIRED, responded_at=now)
            .returning(Invitation.id)
        )
        return len(result.scalars().all())

    # ----- Notifications -----
    async def list_notifications(
        self, db: AsyncSession, user_id: uuid.UUID, *, unread_only: bool = False
    ) -> list[dict[str, Any]]:
        await set_user_context(db, user_id)
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        rows = (await db.scalars(stmt.order_by(Notification.created_at.desc()).limit(200))).all()
        return [
            {
                "id": str(n.id),
                "user_id": str(n.user_id),
                "type": n.type,
                "payload": n.payload,
                "read_at": n.read_at.isoformat() if n.read_at else None,
                "created_at": n.created_at.isoformat(),
            }
            for n in rows
        ]

    async def mark_notification_read(
        self, db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict[str, Any]:
        await set_user_context(db, user_id)
        notif = await db.get(Notification, notification_id)
        if notif is None or notif.user_id != user_id:
            raise AppError(code="NOT_FOUND", status=404, detail="Notification not found.")
        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
        return {
            "id": str(notif.id),
            "read_at": notif.read_at.isoformat(),
        }

    # ----- Internal helpers -----
    async def _push_notification(
        self, db: AsyncSession, *, user_id: uuid.UUID, kind: str, payload: dict[str, Any]
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=_kind_to_notification_type(kind),
            payload={"kind": kind, **payload},
        )
        db.add(notif)
        await db.flush()
        await notification_hub.publish(
            user_id,
            {
                "kind": kind,
                "notification_id": str(notif.id),
                "payload": payload,
                "created_at": notif.created_at.isoformat(),
            },
        )
        return notif

    async def _broadcast_to_participants(
        self,
        db: AsyncSession,
        *,
        participants: list[uuid.UUID],
        event: dict[str, Any],
    ) -> None:
        for uid in participants:
            await notification_hub.publish(uid, event)

    @staticmethod
    def _invitation_to_out(inv: Invitation) -> InvitationOut:
        return InvitationOut(
            id=inv.id,
            from_user_id=inv.from_user_id,
            to_user_id=inv.to_user_id,
            to_email=inv.to_email,
            type=inv.type,
            status=inv.status,
            expires_at=inv.expires_at,
            responded_at=inv.responded_at,
            created_at=inv.created_at,
        )


def _conversation_type_from_invitation(t: str) -> str:
    if t == InvitationType.DOCTOR:
        return ConversationType.DOCTOR
    if t == InvitationType.AGENCY:
        return ConversationType.AGENCY
    return ConversationType.FAMILY


def _kind_to_notification_type(kind: str) -> str:
    if kind.startswith("message"):
        return NotificationType.MESSAGE
    if kind.startswith("invitation"):
        return NotificationType.INVITATION
    return NotificationType.SYSTEM


messaging_service = MessagingService()
