import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.fitness import (
    FitnessLogCreate,
    FitnessLogOut,
    FitnessLogRangeQuery,
    FitnessScoreOut,
    FitnessTargetCreate,
    FitnessTargetOut,
)
from app.services.fitness_service import fitness_service

router = APIRouter(prefix="/fitness", tags=["fitness"])


@router.post("/logs", response_model=FitnessLogOut, status_code=201)
async def log_activity(
    payload: FitnessLogCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FitnessLogOut:
    entry = await fitness_service.log_activity(db, current_user.id, payload)
    return FitnessLogOut.model_validate(entry)


@router.get("/logs", response_model=list[FitnessLogOut])
async def list_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    range: Annotated[Literal["week", "month"], Query()] = "week",
) -> list[FitnessLogOut]:
    FitnessLogRangeQuery(range=range)
    rows = await fitness_service.list_logs(db, current_user.id, range=range)
    return [FitnessLogOut.model_validate(r) for r in rows]


@router.post("/targets", response_model=FitnessTargetOut, status_code=201)
async def set_target(
    payload: FitnessTargetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FitnessTargetOut:
    target = await fitness_service.set_target(db, current_user.id, payload)
    return FitnessTargetOut.model_validate(target)


@router.get("/targets", response_model=list[FitnessTargetOut])
async def list_targets(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FitnessTargetOut]:
    rows = await fitness_service.list_targets(db, current_user.id)
    return [FitnessTargetOut.model_validate(r) for r in rows]


@router.get("/score", response_model=FitnessScoreOut)
async def get_fitness_score(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FitnessScoreOut:
    result = await fitness_service.compute_fitness_score(db, current_user.id)
    return FitnessScoreOut(**result)
