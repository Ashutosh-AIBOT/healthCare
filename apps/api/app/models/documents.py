"""Documents, jobs, report values, and RAG chunks (M4–M6 walking skeleton)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DocumentStatus:
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.QUEUED, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False, default="application/pdf")
    byte_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.UPLOADED, nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)


class LabReportValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lab_report_values"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    analyte_code: Mapped[str] = mapped_column(String(64), nullable=False)
    analyte_name: Mapped[str] = mapped_column(String(120), nullable=False)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Embedding stored as JSON list for M6 skeleton (pgvector upgrade later)
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
