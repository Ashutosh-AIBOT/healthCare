"""Import reviewed food CSV rows into the Learn catalog.

This deliberately accepts a local reviewed export instead of silently scraping
third-party pages. It keeps source provenance and can be rerun safely for the
same source/version.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.learn import LearnCategory, LearnItem, LearnSource


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:70] or "food-item"


def number(value: str | None) -> float | None:
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


async def get_or_create_source(db: AsyncSession, args: argparse.Namespace, digest: str) -> LearnSource:
    source = await db.scalar(
        select(LearnSource).where(
            LearnSource.name == args.source_name,
            LearnSource.version == args.source_version,
        )
    )
    if source:
        source.url = args.source_url
        source.license = args.license
        source.retrieved_at = datetime.now(timezone.utc)
        source.content_hash = digest
        return source
    source = LearnSource(
        name=args.source_name,
        url=args.source_url,
        license=args.license,
        version=args.source_version,
        retrieved_at=datetime.now(timezone.utc),
        content_hash=digest,
    )
    db.add(source)
    await db.flush()
    return source


async def import_foods(args: argparse.Namespace) -> int:
    path = Path(args.food_csv).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        source = await get_or_create_source(db, args, digest)
        category = await db.scalar(select(LearnCategory).where(LearnCategory.slug == args.category_slug))
        if category is None:
            category = LearnCategory(
                slug=args.category_slug,
                title=args.category_title,
                kind="food",
                description="Imported food and nutrition references.",
                sort_order=100,
            )
            db.add(category)
            await db.flush()

        imported = 0
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                title = (row.get("name") or row.get("title") or "").strip()
                if not title:
                    continue
                slug = slugify(title)
                item = await db.scalar(select(LearnItem).where(LearnItem.slug == slug))
                nutrition = {
                    key: value
                    for key, value in {
                        "calories": number(row.get("calories") or row.get("energy_kcal")),
                        "protein_g": number(row.get("protein_g") or row.get("protein")),
                        "carbohydrates_g": number(row.get("carbohydrates_g") or row.get("carbs_g")),
                        "fat_g": number(row.get("fat_g") or row.get("total_fat_g")),
                        "fiber_g": number(row.get("fiber_g") or row.get("dietary_fiber_g")),
                        "serving_size": row.get("serving_size"),
                    }.items()
                    if value is not None
                }
                values = {
                    "category_id": category.id,
                    "title": title[:120],
                    "summary": (row.get("summary") or "").strip() or None,
                    "content": (row.get("content") or "").strip() or None,
                    "nutrition": nutrition or None,
                    "source_id": source.id,
                }
                if item is None:
                    db.add(LearnItem(slug=slug, sort_order=imported, **values))
                else:
                    for key, value in values.items():
                        setattr(item, key, value)
                imported += 1
                if args.limit and imported >= args.limit:
                    break
        await db.commit()
    await engine.dispose()
    return imported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--food-csv", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--category-slug", default="imported-foods")
    parser.add_argument("--category-title", default="Imported foods")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


if __name__ == "__main__":
    print(f"Imported {asyncio.run(import_foods(parse_args()))} food records")
