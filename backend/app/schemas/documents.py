"""Schemas for documents, jobs, and AI ask (M4–M6 walking skeleton)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UploadUrlRequest(BaseModel):
    member_id: uuid.UUID
    filename: str = Field(max_length=255)
    content_type: str = Field(default="application/pdf", max_length=120)
    byte_size: int = Field(default=0, ge=0)


class UploadUrlResponse(BaseModel):
    document_id: uuid.UUID
    object_key: str
    upload_url: str
    expires_in: int = 900


class DocumentConfirmRequest(BaseModel):
    document_id: uuid.UUID
    idempotency_key: str | None = Field(default=None, max_length=120)


class DocumentConfirmResponse(BaseModel):
    job_id: uuid.UUID
    document_id: uuid.UUID


class DocumentOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    member_id: uuid.UUID
    filename: str
    content_type: str
    byte_size: int
    status: str
    job_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    kind: str
    status: str
    progress: int
    error_code: str | None = None
    result: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AiAskRequest(BaseModel):
    member_id: uuid.UUID
    question: str = Field(min_length=1, max_length=4000)
    document_id: uuid.UUID | None = None
