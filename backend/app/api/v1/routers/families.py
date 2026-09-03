from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.family import FamilyCreate
from app.services.family_service import family_service

router = APIRouter(prefix="/families", tags=["families"])


@router.post("/", status_code=201)
async def create_family(
    payload: FamilyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    family = await family_service.create_family(db, current_user.id, payload.name)
    return {"id": family.id, "name": family.name}


@router.get("/me")
async def get_my_family(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict | None:
    family = await family_service.get_my_family(db, current_user.id)
    if family is None:
        return None
    return {"id": family.id, "name": family.name}
