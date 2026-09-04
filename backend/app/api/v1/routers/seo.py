import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import AppError
from app.models.user import User
from app.schemas.seo import (
    ProviderSEOPageCreate,
    ProviderSEOPageOut,
    SEOCheckRequest,
    SEOCheckResponse,
    SEOPageCreate,
    SEOPageOut,
)
from app.services.seo_service import seo_service

router = APIRouter(prefix="/seo", tags=["seo"])


def _require_admin(current_user: User) -> None:
    if current_user.role not in ("platform_admin", "support_agent"):
        raise AppError(code="FORBIDDEN", status=403, detail="Admin access required.")


@router.get("/pages", response_model=list[SEOPageOut])
async def list_seo_pages(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[SEOPageOut]:
    _require_admin(current_user)
    pages = await seo_service.list_seo_pages(db)
    return [SEOPageOut.model_validate(page) for page in pages]


@router.post("/pages", status_code=201, response_model=SEOPageOut)
async def upsert_seo_page(
    payload: SEOPageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SEOPageOut:
    _require_admin(current_user)
    page = await seo_service.upsert_seo_page(db, payload.route, payload)
    return SEOPageOut.model_validate(page)


@router.get("/pages/{route}", response_model=SEOPageOut)
async def get_seo_page(
    route: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SEOPageOut:
    _require_admin(current_user)
    page = await seo_service.get_seo_page(db, route)
    if page is None:
        raise AppError(code="SEO_PAGE_NOT_FOUND", status=404, detail="SEO page not found.")
    return SEOPageOut.model_validate(page)


@router.post("/check", response_model=SEOCheckResponse)
async def check_seo(
    payload: SEOCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SEOCheckResponse:
    _require_admin(current_user)
    checks, overall_ok = await seo_service.check_seo(db, payload)
    return SEOCheckResponse(checks=checks, overall_ok=overall_ok)


@router.get("/providers/{provider_profile_id}/pages", response_model=list[ProviderSEOPageOut])
async def list_provider_pages(
    provider_profile_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProviderSEOPageOut]:
    _require_admin(current_user)
    pid = uuid.UUID(provider_profile_id)
    pages = await seo_service.list_provider_pages(db, pid)
    return [ProviderSEOPageOut.model_validate(page) for page in pages]


@router.post("/providers/{provider_profile_id}/pages", status_code=201, response_model=ProviderSEOPageOut)
async def register_provider_page(
    provider_profile_id: str,
    payload: ProviderSEOPageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProviderSEOPageOut:
    _require_admin(current_user)
    payload.provider_profile_id = provider_profile_id
    page = await seo_service.register_provider_page(db, payload)
    return ProviderSEOPageOut.model_validate(page)
