"""M4–M6 walking skeleton: document job flow + triage (in-process, no Celery broker)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.ai import guardrails, triage
from app.ai.rag import build_cited_answer
from app.core.security import hash_password
from app.models.documents import Document, DocumentChunk, DocumentStatus, Job, JobStatus, LabReportValue
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from app.services.document_service import document_service
from app.tasks.document_tasks import process_document_with_session


async def _tables_ready(db) -> bool:
    try:
        await db.execute(text("SELECT 1 FROM jobs LIMIT 0"))
        await db.execute(text("SELECT 1 FROM documents LIMIT 0"))
        return True
    except Exception:
        await db.rollback()
        return False


@pytest.mark.asyncio
async def test_triage_red_flag_before_model():
    verdict = triage.screen("I have severe chest pain and can't breathe")
    assert verdict.flagged is True
    assert verdict.matched_rule is not None
    msg = triage.emergency_response()
    assert "112" in msg or "108" in msg
    assert "urgent" in msg.lower() or "emergency" in msg.lower()


@pytest.mark.asyncio
async def test_guardrails_append_disclaimer():
    out = guardrails.apply_guardrails("Hemoglobin is 13.2 g/dL on your report.")
    assert "diagnose" in out.lower() or "clinician" in out.lower() or "doctor" in out.lower()
    cleaned = guardrails.strip_diagnosis_language("You have diabetes and we prescribe metformin.")
    assert "prescribe" not in cleaned.lower() or "clinician" in cleaned.lower()


@pytest.mark.asyncio
async def test_documents_skeleton_job_flow(db):
    if not await _tables_ready(db):
        pytest.skip(
            "jobs/documents tables missing — run alembic upgrade to 012 before integration test"
        )

    family = Family(name="Skeleton Family")
    db.add(family)
    await db.flush()

    user = User(
        email=f"skel-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("SecurePass1!"),
        full_name="Skeleton",
        handle=f"skel{uuid.uuid4().hex[:8]}",
        family_id=family.id,
        role="family_owner",
    )
    db.add(user)
    await db.flush()

    member = FamilyMember(
        family_id=family.id,
        user_id=user.id,
        is_dependent=False,
        timezone="Asia/Kolkata",
    )
    db.add(member)
    await db.flush()

    upload = await document_service.create_upload_url(
        db,
        family_id=family.id,
        member_id=member.id,
        uploaded_by_user_id=user.id,
        filename="report.pdf",
        content_type="application/pdf",
        byte_size=1024,
    )
    document_id = upload["document_id"]

    # Mock Celery enqueue; process in-process on the same session
    original_enqueue = document_service._enqueue_process
    document_service._enqueue_process = lambda _did: None
    try:
        confirmed = await document_service.confirm_upload(
            db,
            family_id=family.id,
            document_id=document_id,
            idempotency_key=f"skel-{document_id}",
        )
    finally:
        document_service._enqueue_process = original_enqueue

    job_id = confirmed["job_id"]
    await process_document_with_session(db, document_id)

    doc = await db.get(Document, document_id)
    assert doc is not None
    assert doc.status == DocumentStatus.READY

    job = await db.get(Job, job_id)
    assert job is not None
    assert job.status == JobStatus.SUCCEEDED
    assert job.progress == 100

    values = (
        await db.execute(select(LabReportValue).where(LabReportValue.document_id == document_id))
    ).scalars().all()
    assert len(values) == 2
    names = {v.analyte_name for v in values}
    assert "Hemoglobin" in names
    assert "Glucose" in names

    chunks = (
        await db.execute(select(DocumentChunk).where(DocumentChunk.document_id == document_id))
    ).scalars().all()
    assert len(chunks) >= 2
    assert chunks[0].embedding is not None

    answer = await build_cited_answer(
        db, member_id=member.id, question="What is my hemoglobin?", document_id=document_id
    )
    assert "Hemoglobin" in answer.text or "13.2" in answer.text
    assert answer.citations
