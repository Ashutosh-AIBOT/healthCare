"""Document upload confirm, list, and job status (M4 walking skeleton)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.integrations import storage
from app.models.documents import Document, DocumentStatus, Job
from app.models.family_member import FamilyMember
from app.services.job_service import job_service

logger = logging.getLogger(__name__)


class DocumentService:
    async def create_upload_url(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        filename: str,
        content_type: str = "application/pdf",
        byte_size: int = 0,
    ) -> dict[str, Any]:
        await self._assert_member_in_family(db, member_id, family_id)
        if content_type not in ("application/pdf", "application/x-pdf"):
            raise AppError(code="UNSUPPORTED_MEDIA", status=415, detail="Only PDF uploads are supported.")
        if byte_size > 25 * 1024 * 1024:
            raise AppError(code="PAYLOAD_TOO_LARGE", status=413, detail="File exceeds size limit.")

        object_key = storage.make_object_key(family_id, filename)
        storage.ensure_bucket()
        upload_url = storage.presign_put(object_key, content_type=content_type)

        doc = Document(
            family_id=family_id,
            member_id=member_id,
            uploaded_by_user_id=uploaded_by_user_id,
            object_key=object_key,
            filename=filename[:255],
            content_type=content_type,
            byte_size=byte_size,
            status=DocumentStatus.UPLOADED,
        )
        db.add(doc)
        await db.flush()
        # Never log filename or object contents (PHI risk)
        logger.info("upload_url created document_id=%s family_id=%s", doc.id, family_id)
        return {
            "document_id": doc.id,
            "object_key": object_key,
            "upload_url": upload_url,
            "expires_in": 900,
        }

    async def confirm_upload(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        document_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> dict[str, uuid.UUID]:
        doc = await db.get(Document, document_id)
        if doc is None or doc.family_id != family_id:
            raise AppError(code="NOT_FOUND", status=404, detail="Document not found.")

        if doc.job_id is not None:
            return {"job_id": doc.job_id, "document_id": doc.id}

        job = await job_service.create_job(
            db,
            family_id=family_id,
            kind="process_document",
            payload={"document_id": str(doc.id)},
            idempotency_key=idempotency_key,
        )
        doc.job_id = job.id
        doc.status = DocumentStatus.PROCESSING
        await db.flush()

        self._enqueue_process(doc.id)
        logger.info("document queued document_id=%s job_id=%s", doc.id, job.id)
        return {"job_id": job.id, "document_id": doc.id}

    def _enqueue_process(self, document_id: uuid.UUID) -> None:
        from app.tasks.document_tasks import process_document

        try:
            process_document.delay(str(document_id))
        except Exception:
            logger.warning(
                "celery enqueue failed document_id=%s; running inline",
                document_id,
            )
            try:
                process_document.run(str(document_id))
            except Exception:
                logger.exception("inline process_document failed document_id=%s", document_id)

    async def list_documents(self, db: AsyncSession, family_id: uuid.UUID) -> list[Document]:
        result = await db.execute(
            select(Document)
            .where(Document.family_id == family_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_job_status(
        self, db: AsyncSession, *, family_id: uuid.UUID, job_id: uuid.UUID
    ) -> Job:
        return await job_service.get_job_for_family(db, job_id, family_id)

    async def _assert_member_in_family(
        self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID
    ) -> FamilyMember:
        member = await db.get(FamilyMember, member_id)
        if member is None or member.family_id != family_id or member.deleted_at is not None:
            raise AppError(code="NOT_FOUND", status=404, detail="Member not found.")
        return member


document_service = DocumentService()
