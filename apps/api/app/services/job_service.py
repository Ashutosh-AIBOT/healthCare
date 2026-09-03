"""Job create / progress updates (M4 walking skeleton)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.documents import Job, JobStatus


class JobService:
    async def create_job(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        kind: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Job:
        if idempotency_key:
            existing = await db.scalar(
                select(Job).where(Job.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return existing

        job = Job(
            family_id=family_id,
            kind=kind,
            status=JobStatus.QUEUED,
            progress=0,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        db.add(job)
        await db.flush()
        return job

    async def get_job(self, db: AsyncSession, job_id: uuid.UUID) -> Job | None:
        return await db.get(Job, job_id)

    async def get_job_for_family(
        self, db: AsyncSession, job_id: uuid.UUID, family_id: uuid.UUID
    ) -> Job:
        job = await db.get(Job, job_id)
        if job is None or job.family_id != family_id:
            raise AppError(code="NOT_FOUND", status=404, detail="Job not found.")
        return job

    async def update_progress(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        *,
        status: str | None = None,
        progress: int | None = None,
        error_code: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> Job:
        job = await db.get(Job, job_id)
        if job is None:
            raise AppError(code="NOT_FOUND", status=404, detail="Job not found.")
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if error_code is not None:
            job.error_code = error_code
        if result is not None:
            job.result = result
        await db.flush()
        return job


job_service = JobService()
