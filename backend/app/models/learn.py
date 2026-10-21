"""Learn catalog models — global read-only, auth required.

No family_id/RLS. Admin-only writes later; reads need an authenticated user
so the catalog never leaks to anonymous crawlers beyond the public site.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class LearnCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learn_categories"

    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # food | test_info
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    items: Mapped[list["LearnItem"]] = relationship(back_populates="category", cascade="all, delete-orphan", order_by="LearnItem.sort_order")


class LearnSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learn_sources"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    license: Mapped[str | None] = mapped_column(String(160), nullable=True)
    version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)


class LearnItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learn_items"

    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("learn_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nutrition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    benefits: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    healthy_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("learn_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped["LearnCategory"] = relationship(back_populates="items")


class TestBodyPart(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_body_parts"

    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tests: Mapped[list["BodyTest"]] = relationship(back_populates="body_part", cascade="all, delete-orphan", order_by="BodyTest.sort_order")


class BodyTest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "body_tests"

    body_part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_body_parts.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    what_it_checks: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    fasting_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("learn_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    body_part: Mapped["TestBodyPart"] = relationship(back_populates="tests")
