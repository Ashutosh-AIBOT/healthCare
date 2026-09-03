"""Document upload and job status routes (M4 walking skeleton)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.documents import (
    DocumentConfirmRequest,
    DocumentConfirmResponse,
    DocumentOut,
    JobOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.document_service import document_service

router = APIRouter(tags=["documents"])


def _require_family(user: User) -> uuid.UUID:
    if user.family_id is None:
        raise AppError(code="NO_FAMILY", status=400, detail="User does not belong to a family.")
    return user.family_id


@router.post("/documents/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    payload: UploadUrlRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UploadUrlResponse:
    family_id = _require_family(current_user)
    result = await document_service.create_upload_url(
        db,
        family_id=family_id,
        member_id=payload.member_id,
        uploaded_by_user_id=current_user.id,
        filename=payload.filename,
        content_type=payload.content_type,
        byte_size=payload.byte_size,
    )
    return UploadUrlResponse(**result)


@router.post("/documents", response_model=DocumentConfirmResponse, status_code=202)
async def confirm_document(
    payload: DocumentConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DocumentConfirmResponse:
    family_id = _require_family(current_user)
    key = payload.idempotency_key or idempotency_key
    result = await document_service.confirm_upload(
        db,
        family_id=family_id,
        document_id=payload.document_id,
        idempotency_key=key,
    )
    return DocumentConfirmResponse(**result)


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentOut]:
    family_id = _require_family(current_user)
    docs = await document_service.list_documents(db, family_id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JobOut:
    family_id = _require_family(current_user)
    job = await document_service.get_job_status(db, family_id=family_id, job_id=job_id)
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """SSE progress stream for a job."""
    family_id = _require_family(current_user)
    # Authz check once up front
    await document_service.get_job_status(db, family_id=family_id, job_id=job_id)

    async def event_gen() -> AsyncIterator[str]:
        last_progress = -1
        for _ in range(120):
            job = await document_service.get_job_status(
                db, family_id=family_id, job_id=job_id
            )
            if job.progress != last_progress or job.status in ("succeeded", "failed"):
                last_progress = job.progress
                payload = {
                    "job_id": str(job.id),
                    "status": job.status,
                    "progress": job.progress,
                    "error_code": job.error_code,
                }
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
            if job.status in ("succeeded", "failed"):
                yield f"event: done\ndata: {json.dumps({'status': job.status})}\n\n"
                return
            await asyncio.sleep(0.5)
        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
