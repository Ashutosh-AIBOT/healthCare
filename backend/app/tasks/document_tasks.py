"""Celery tasks for document processing (M4–M6 walking skeleton)."""

from __future__ import annotations

import asyncio
import io
import logging
import re
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
from app.integrations import storage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

def _extract_pdf_pages(data: bytes) -> list[tuple[int, str]]:
    """Extract text while preserving page boundaries for citations."""
    if not data:
        return []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return [(index + 1, (page.extract_text() or "").strip()) for index, page in enumerate(reader.pages)]
    except Exception:
        logger.exception("PDF text extraction failed")
        return []


def _extract_report_values(pages: list[tuple[int, str]]) -> list[dict]:
    """Parse only lines that visibly include a reference range; never invent values."""
    values: list[dict] = []
    pattern = re.compile(
        r"^(?P<name>[A-Za-z][A-Za-z0-9 /()%-]{2,80}?)\s+(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-zµ/%^0-9]+)?\s*(?:\(?\s*(?:ref(?:erence)?|range)\s*[:=]?\s*)?(?P<low>-?\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(?P<high>-?\d+(?:\.\d+)?)\s*\)?$",
        re.IGNORECASE,
    )
    for page, text in pages:
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            if not line or not re.search(r"\b(?:ref(?:erence)?|range)\b|\d\s*(?:-|to|–)\s*\d", line, re.IGNORECASE):
                continue
            match = pattern.match(line)
            if not match:
                continue
            name = match.group("name").strip(" :-")
            value = float(match.group("value"))
            low = float(match.group("low"))
            high = float(match.group("high"))
            values.append({
                "analyte_code": re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")[:64],
                "analyte_name": name[:120],
                "value_num": value,
                "unit": match.group("unit"),
                "ref_low": low,
                "ref_high": high,
                "flag": "within_range" if low <= value <= high else "outside_range",
                "page": page,
                "confidence": 0.65,
            })
    return values[:200]


def _chunk_pages(pages: list[tuple[int, str]], chunk_size: int = 1600) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    index = 0
    for page, text in pages:
        if not text:
            continue
        for offset in range(0, len(text), chunk_size):
            content = text[offset:offset + chunk_size].strip()
            if content:
                chunks.append((index, page, content))
                index += 1
    return chunks


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

    pages = _extract_pdf_pages(storage.get_object_bytes(doc.object_key))
    if not pages or not any(text for _, text in pages):
        raise ValueError("The uploaded PDF has no extractable text. Use a text-based PDF or OCR it before upload.")

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

    extracted_values = _extract_report_values(pages)
    for value in extracted_values:
        db.add(
            LabReportValue(
                document_id=doc.id,
                member_id=doc.member_id,
                family_id=doc.family_id,
                analyte_code=value["analyte_code"],
                analyte_name=value["analyte_name"],
                value_num=value["value_num"],
                unit=value["unit"],
                ref_low=value["ref_low"],
                ref_high=value["ref_high"],
                flag=value["flag"],
                confidence=value["confidence"],
                page=value["page"],
            )
        )

    if job_id:
        await job_service.update_progress(db, job_id, progress=70)

    chunk_texts = _chunk_pages(pages)
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
            result={"document_id": str(doc.id), "values": len(extracted_values), "chunks": len(chunk_texts)},
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
