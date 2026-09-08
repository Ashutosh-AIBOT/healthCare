from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.learn import BodyTestOut, LearnCategoryOut, LearnItemOut, LearnSearchResult, TestBodyPartOut
from app.services.learn_service import learn_service

router = APIRouter(prefix="/learn", tags=["learn"])


@router.get("/categories", response_model=list[LearnCategoryOut])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    kind: str | None = Query(default=None, pattern="^(food|test_info)$"),
):
    return await learn_service.list_categories(db, kind)


@router.get("/categories/{slug}/items", response_model=list[LearnItemOut])
async def list_category_items(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await learn_service.list_items(db, slug)


@router.get("/items/{slug}", response_model=LearnItemOut)
async def get_item(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await learn_service.get_item(db, slug)


@router.get("/body-parts", response_model=list[TestBodyPartOut])
async def list_body_parts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await learn_service.list_body_parts(db)


@router.get("/body-parts/{slug}/tests", response_model=list[BodyTestOut])
async def list_body_tests(
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return await learn_service.list_tests(db, slug)


@router.get("/tests", response_model=list[BodyTestOut])
async def list_tests_by_fasting(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    fasting: bool | None = Query(default=None),
):
    return await learn_service.list_tests_by_fasting(db, fasting)


@router.get("/search", response_model=LearnSearchResult)
async def search_learn(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    q: str = Query(min_length=1),
):
    return await learn_service.search(db, q)
