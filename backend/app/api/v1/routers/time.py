from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.db.session import set_tenant_context
from app.models.user import User
from app.schemas.time import (
    DayBlockStatusIn,
    DayBlockStatusOut,
    DayPlanBlockOut,
    DayPlanOut,
    HolidayRuleOut,
    HolidayRulesIn,
    TimeBlockIn,
    TimeBlockOut,
    TimeBlockPatch,
    TimeEntryIn,
    TimeEntryOut,
    TimeTimetableOut,
    TodoIn,
    TodoOut,
    TodoPatch,
)
from app.services.time_service import time_service

router = APIRouter(prefix="/time", tags=["time"])


def _ctx(user: User) -> tuple[uuid.UUID, uuid.UUID]:
    if user.family_id is None:
        from app.core.errors import AppError

        raise AppError(code="NO_FAMILY", status=400, detail="No family")
    return user.family_id, user.id


@router.get("/timetables", response_model=list[TimeTimetableOut])
async def list_timetables(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.list_timetables(db, fam, uid)


@router.patch("/timetables/{timetable_id}", response_model=TimeTimetableOut)
async def patch_timetable(timetable_id: uuid.UUID, payload: dict, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.update_timetable(db, fam, uid, timetable_id, payload.get("name"))


@router.post("/timetables/{timetable_id}/blocks", response_model=TimeBlockOut, status_code=201)
async def create_block(timetable_id: uuid.UUID, payload: TimeBlockIn, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.create_block(db, fam, uid, timetable_id, payload.model_dump())


@router.patch("/blocks/{block_id}", response_model=TimeBlockOut)
async def patch_block(block_id: uuid.UUID, payload: TimeBlockPatch, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.update_block(db, fam, uid, block_id, payload.model_dump(exclude_none=True))


@router.delete("/blocks/{block_id}", status_code=204)
async def delete_block(block_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    await time_service.delete_block(db, fam, uid, block_id)
    return None


@router.get("/todos", response_model=list[TodoOut])
async def list_todos(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)], due_date: date | None = Query(default=None)):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.list_todos(db, fam, uid, due_date)


@router.post("/todos", response_model=TodoOut, status_code=201)
async def create_todo(payload: TodoIn, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.create_todo(db, fam, uid, payload.model_dump())


@router.patch("/todos/{todo_id}", response_model=TodoOut)
async def patch_todo(todo_id: uuid.UUID, payload: TodoPatch, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.update_todo(db, fam, uid, todo_id, payload.model_dump(exclude_none=True))


@router.delete("/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    await time_service.delete_todo(db, fam, uid, todo_id)
    return None


@router.get("/holiday-rules", response_model=list[HolidayRuleOut])
async def list_holiday_rules(db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.list_holiday_rules(db, fam, uid)


@router.put("/holiday-rules", response_model=list[HolidayRuleOut])
async def put_holiday_rules(payload: HolidayRulesIn, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.set_holiday_rules(db, fam, uid, payload.weekly_weekday, payload.specific_dates)


@router.get("/day/{iso_date}/timetable-kind")
async def day_kind(iso_date: date, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    kind = await time_service.get_day_timetable_kind(db, fam, uid, iso_date)
    return {"date": iso_date.isoformat(), "kind": kind}


@router.put("/day/{iso_date}/blocks/status", response_model=DayBlockStatusOut)
async def put_day_block_status(iso_date: date, payload: DayBlockStatusIn, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.set_day_block_status(db, fam, uid, iso_date, payload.block_id, payload.status)


@router.get("/day/{iso_date}/stats")
async def day_stats(iso_date: date, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.get_stats(db, fam, uid, iso_date)


@router.get("/day/{iso_date}/plan", response_model=DayPlanOut)
async def day_plan(iso_date: date, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.get_day_plan(db, fam, uid, iso_date)


@router.post("/day/{iso_date}/checkin", response_model=TimeEntryOut, status_code=201)
async def day_checkin(iso_date: date, payload: TimeEntryIn, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.log_checkin(db, fam, uid, iso_date, payload.block_id, payload.actual_title, payload.matched, payload.duration_minutes)


@router.get("/day/{iso_date}/entries", response_model=list[TimeEntryOut])
async def day_entries(iso_date: date, db: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    fam, uid = _ctx(current_user)
    await set_tenant_context(db, fam)
    return await time_service.list_entries(db, fam, uid, iso_date)
