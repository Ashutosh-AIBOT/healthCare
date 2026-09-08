"""Time management models: timetables, blocks, todos, holiday rules, day block status."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class TimeTimetableKind:
    PRODUCTIVE = "productive"
    BACKUP = "backup"
    HOLIDAY = "holiday"


class TodoStatus:
    PENDING = "pending"
    DONE = "done"


class TodoPriority:
    NORMAL = "normal"  # default
    IMPORTANT = "important"  # highlighted stronger
    LESS = "less"  # less care


class DayBlockStatusEnum:
    DONE = "done"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class TimeTimetable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "time_timetables"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # productive/backup/holiday
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    blocks: Mapped[list["TimeBlock"]] = relationship(back_populates="timetable", cascade="all, delete-orphan", order_by="TimeBlock.start_minute")


class TimeBlock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "time_blocks"

    timetable_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("time_timetables.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-1439
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=TodoPriority.NORMAL)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    timetable: Mapped["TimeTimetable"] = relationship(back_populates="blocks")


class Todo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "todos"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TodoStatus.PENDING)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default=TodoPriority.NORMAL)
    timetable_block_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("time_blocks.id", ondelete="SET NULL"), nullable=True, index=True)


class HolidayRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holiday_rules"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # weekly/specific
    weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=Sunday ... 6=Saturday
    specific_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class DayBlockStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "day_block_status"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    block_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("time_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # done/partial/skipped


class TimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "time_entries"

    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    block_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("time_blocks.id", ondelete="CASCADE"), nullable=False, index=True)
    actual_title: Mapped[str] = mapped_column(String(200), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
