import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.provider import ProviderProfile
from app.models.seo import SEOPage, ProviderSEOPage
from app.schemas.seo import SEOCheckItem, ProviderSEOPageCreate, SEOPageCreate


class SEOService:
    async def upsert_seo_page(self, db: AsyncSession, route: str, payload: SEOPageCreate) -> SEOPage:
        result = await db.execute(select(SEOPage).where(SEOPage.route == route))
        page = result.scalar_one_or_none()
        now = datetime.now(UTC)
        if page is None:
            page = SEOPage(
                route=route,
                title=payload.title,
                description=payload.description,
                canonical_url=payload.canonical_url,
                robots_noindex=payload.robots_noindex,
                robots_nofollow=payload.robots_nofollow,
                quality_gate_passed=payload.quality_gate_passed,
                last_verified_at=now if payload.quality_gate_passed else None,
            )
            db.add(page)
        else:
            page.title = payload.title
            page.description = payload.description
            page.canonical_url = payload.canonical_url
            page.robots_noindex = payload.robots_noindex
            page.robots_nofollow = payload.robots_nofollow
            page.quality_gate_passed = payload.quality_gate_passed
            page.last_verified_at = now if payload.quality_gate_passed else page.last_verified_at
        await db.flush()
        return page

    async def get_seo_page(self, db: AsyncSession, route: str) -> SEOPage | None:
        result = await db.execute(select(SEOPage).where(SEOPage.route == route))
        return result.scalar_one_or_none()

    async def list_seo_pages(self, db: AsyncSession) -> list[SEOPage]:
        result = await db.execute(select(SEOPage).order_by(SEOPage.created_at.desc()))
        return list(result.scalars().all())

    async def register_provider_page(self, db: AsyncSession, payload: ProviderSEOPageCreate) -> ProviderSEOPage:
        profile = await db.get(ProviderProfile, uuid.UUID(payload.provider_profile_id))
        if profile is None:
            raise AppError(code="PROVIDER_PROFILE_NOT_FOUND", status=404, detail="Provider profile not found.")
        page = ProviderSEOPage(
            provider_profile_id=profile.id,
            route=payload.route,
            quality_score=payload.quality_score,
            is_indexable=payload.is_indexable,
            last_crawled_at=payload.last_crawled_at,
            crawl_error=payload.crawl_error,
        )
        db.add(page)
        await db.flush()
        return page

    async def list_provider_pages(self, db: AsyncSession, provider_profile_id: uuid.UUID) -> list[ProviderSEOPage]:
        result = await db.execute(
            select(ProviderSEOPage).where(ProviderSEOPage.provider_profile_id == provider_profile_id).order_by(ProviderSEOPage.created_at.desc())
        )
        return list(result.scalars().all())

    async def check_seo(self, db: AsyncSession, request: SEOCheckRequest) -> tuple[list[SEOCheckItem], bool]:
        checks: list[SEOCheckItem] = []
        overall_ok = True
        routes = request.routes[:50]
        for route in routes:
            page = await self.get_seo_page(db, route)
            issues: list[str] = []
            if page is None:
                issues.append("missing")
                checks.append(
                    SEOCheckItem(
                        route=route,
                        exists=False,
                        issues=issues,
                    )
                )
                overall_ok = False
                continue
            title_len = len(page.title) if page.title else 0
            desc_len = len(page.description) if page.description else 0
            has_canonical = bool(page.canonical_url)
            if not (30 <= title_len <= 70):
                issues.append(f"title_length={title_len} (expected 30-70)")
            if not (120 <= desc_len <= 160):
                issues.append(f"description_length={desc_len} (expected 120-160)")
            if not has_canonical:
                issues.append("missing_canonical")
            if page.robots_noindex:
                issues.append("noindex_set")
            if page.robots_nofollow:
                issues.append("nofollow_set")
            if not page.quality_gate_passed:
                issues.append("quality_gate_not_passed")
            if issues:
                overall_ok = False
            checks.append(
                SEOCheckItem(
                    route=route,
                    exists=True,
                    title_length=title_len,
                    description_length=desc_len,
                    has_canonical=has_canonical,
                    robots_noindex=page.robots_noindex,
                    robots_nofollow=page.robots_nofollow,
                    quality_gate_passed=page.quality_gate_passed,
                    issues=issues,
                )
            )
        return checks, overall_ok


seo_service = SEOService()
