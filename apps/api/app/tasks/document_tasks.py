"""Celery tasks for document processing (M4–M6 walking skeleton)."""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag import fake_embedding
from app.db.session import AsyncSessionLocal, set_rls_bypass, set_tenant_context
from app.models.documents import (
    Document,
    DocumentChunk,
    DocumentStatus,
    JobStatus,
    LabReportValue,
)
from app.services.job_service import job_service
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Stub extracted values for the walking skeleton (no real OCR / LLM).
_STUB_VALUES = (
    {
        "analyte_code": "HGB",
        "analyte_name": "Hemoglobin",
        "value_num": 13.2,
        "unit": "g/dL",
        "ref_low": 12.0,
        "ref_high": 17.0,
        "flag": "within_range",
        "page": 1,
    },
    {
        "analyte_code": "GLU",
        "analyte_name": "Glucose",
        "value_num": 98.0,
        "unit": "mg/dL",
        "ref_low": 70.0,
        "ref_high": 99.0,
        "flag": "within_range",
        "page": 1,
    },
)


async def process_document_with_session(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Core processing — usable from Celery or in-process tests."""
    doc = await db.get(Document, document_id)
    if doc is None:
        logger.warning("process_document missing document_id=%s", document_id)
        return

    await set_tenant_context(db, doc.family_id)
    job_id = doc.job_id

    if job_id:
        await job_service.update_progress(
            db, job_id, status=JobStatus.RUNNING, progress=10
        )

    doc.status = DocumentStatus.PROCESSING
    await db.flush()

    if job_id:
        await job_service.update_progress(db, job_id, progress=40)

    existing_vals = (
        await db.execute(select(LabReportValue).where(LabReportValue.document_id == doc.id))
    ).scalars().all()
    for row in existing_vals:
        await db.delete(row)
    existing_chunks = (
        await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    ).scalars().all()
    for row in existing_chunks:
        await db.delete(row)
    await db.flush()

    for stub in _STUB_VALUES:
        db.add(
            LabReportValue(
                document_id=doc.id,
                member_id=doc.member_id,
                family_id=doc.family_id,
                analyte_code=stub["analyte_code"],
                analyte_name=stub["analyte_name"],
                value_num=stub["value_num"],
                unit=stub["unit"],
                ref_low=stub["ref_low"],
                ref_high=stub["ref_high"],
                flag=stub["flag"],
                confidence=0.95,
                page=stub["page"],
            )
        )

    if job_id:
        await job_service.update_progress(db, job_id, progress=70)

    chunk_texts = (
        (
            0,
            1,
            "Hemoglobin 13.2 g/dL (reference 12.0–17.0). "
            "This value appears on page 1 of the uploaded report.",
        ),
        (
            1,
            1,
            "Glucose 98 mg/dL (reference 70–99). "
            "This value appears on page 1 of the uploaded report.",
        ),
    )
    for idx, page, content in chunk_texts:
        db.add(
            DocumentChunk(
                document_id=doc.id,
                family_id=doc.family_id,
                member_id=doc.member_id,
                chunk_index=idx,
                content=content,
                page=page,
                embedding=fake_embedding(content),
            )
        )

    doc.status = DocumentStatus.READY
    if job_id:
        await job_service.update_progress(
            db,
            job_id,
            status=JobStatus.SUCCEEDED,
            progress=100,
            result={"document_id": str(doc.id), "values": len(_STUB_VALUES)},
        )
    await db.flush()
    logger.info("process_document succeeded document_id=%s", document_id)


async def _process_document_async(document_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await set_rls_bypass(db, True)
            await process_document_with_session(db, document_id)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("process_document failed document_id=%s", document_id)
            async with AsyncSessionLocal() as err_db:
                await set_rls_bypass(err_db, True)
                doc = await err_db.get(Document, document_id)
                if doc is not None:
                    await set_tenant_context(err_db, doc.family_id)
                    doc.status = DocumentStatus.FAILED
                    if doc.job_id:
                        await job_service.update_progress(
                            err_db,
                            doc.job_id,
                            status=JobStatus.FAILED,
                            error_code="DOCUMENT_PROCESS_FAILED",
                            progress=100,
                        )
                    await err_db.commit()
            raise


def process_document_sync(document_id: str | uuid.UUID) -> None:
    """In-process entry point (Celery worker / scripts)."""
    did = uuid.UUID(str(document_id))
    asyncio.run(_process_document_async(did))


@celery_app.task(name="app.tasks.document_tasks.process_document", bind=True, max_retries=3)
def process_document(self, document_id: str) -> None:  # noqa: ARG001
    process_document_sync(document_id)
