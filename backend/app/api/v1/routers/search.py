from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.search import ProviderSearchFilters, ProviderSearchResult
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/providers", response_model=list[ProviderSearchResult])
async def search_providers(
    filters: Annotated[ProviderSearchFilters, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProviderSearchResult]:
    items, _ = await search_service.search_providers(db, filters)
    return items
