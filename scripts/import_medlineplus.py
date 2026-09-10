"""Import a small, reviewed MedlinePlus health-topic seed into Learn.

MedlinePlus is queried through its official XML service. This is intentionally
term-based and rate-limited; it is not an uncontrolled site scraper.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.learn import BodyTest, LearnCategory, LearnItem, LearnSource, TestBodyPart

BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"
DEFAULT_TERMS = (
    "blood glucose test",
    "cholesterol levels test",
    "complete blood count",
    "creatinine test",
    "hemoglobin test",
    "thyroid tests",
    "vitamin D test",
)

BODY_PARTS = {
    "blood glucose test": ("metabolic", "Metabolic health"),
    "cholesterol levels test": ("heart", "Heart and cholesterol"),
    "complete blood count": ("blood", "Blood and anemia"),
    "creatinine test": ("kidney", "Kidney health"),
    "hemoglobin test": ("blood", "Blood and anemia"),
    "thyroid tests": ("thyroid", "Thyroid health"),
    "vitamin D test": ("vitamins", "Vitamins and nutrition"),
}


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:70]


async def category(db: AsyncSession) -> LearnCategory:
    result = await db.scalar(select(LearnCategory).where(LearnCategory.slug == "medlineplus-tests"))
    if result:
        return result
    result = LearnCategory(slug="medlineplus-tests", title="Medical test guides", kind="test_info", description="Official educational test information from MedlinePlus.", sort_order=10)
    db.add(result)
    await db.flush()
    return result


async def body_part(db: AsyncSession, slug: str, name: str, order: int) -> TestBodyPart:
    result = await db.scalar(select(TestBodyPart).where(TestBodyPart.slug == slug))
    if result:
        return result
    result = TestBodyPart(slug=slug, name=name, order_index=order, description="Educational test information; follow your clinician or laboratory instructions.")
    db.add(result)
    await db.flush()
    return result


async def import_topics(terms: list[str]) -> int:
    async with httpx.AsyncClient(timeout=30) as client:
        response_bodies: list[tuple[str, str, str]] = []
        for term in terms:
            response = await client.get(BASE_URL, params={"db": "healthTopics", "term": term, "rettype": "brief", "retmax": 10, "tool": "aarogya_learn"})
            response.raise_for_status()
            response_bodies.append((term, response.text, str(response.url)))

    digest = hashlib.sha256("\n".join(body for _, body, _ in response_bodies).encode()).hexdigest()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    imported = 0
    async with session_factory() as db:
        source = await db.scalar(select(LearnSource).where(LearnSource.name == "MedlinePlus Web Service", LearnSource.version == "healthTopics"))
        if source is None:
            source = LearnSource(name="MedlinePlus Web Service", url="https://medlineplus.gov/about/developers/webservices/", license="Free with attribution", version="healthTopics", retrieved_at=datetime.now(timezone.utc), content_hash=digest)
            db.add(source)
            await db.flush()
        else:
            source.retrieved_at = datetime.now(timezone.utc)
            source.content_hash = digest
        cat = await category(db)
        for term, body, request_url in response_bodies:
            root = ET.fromstring(body)
            selected_part = None
            if term in BODY_PARTS:
                selected_part = await body_part(db, *BODY_PARTS[term], list(BODY_PARTS).index(term))
            for index, document in enumerate(root.findall(".//document")):
                title = next((clean(node.text or "") for node in document.findall("content") if node.attrib.get("name") == "title"), "")
                summary = next((clean(node.text or "") for node in document.findall("content") if node.attrib.get("name", "").lower() == "fullsummary"), "")
                url = document.attrib.get("url") or request_url
                if not title or not summary:
                    continue
                slug = f"medlineplus-{slugify(title)}"
                item = await db.scalar(select(LearnItem).where(LearnItem.slug == slug))
                values = {"category_id": cat.id, "title": title[:120], "summary": summary[:1000], "content": summary, "source_id": source.id}
                if item is None:
                    db.add(LearnItem(slug=slug, sort_order=imported, **values))
                else:
                    for key, value in values.items():
                        setattr(item, key, value)
                imported += 1
                if index == 0 and selected_part is not None:
                    test = await db.scalar(select(BodyTest).where(BodyTest.body_part_id == selected_part.id, BodyTest.name == title[:120]))
                    test_values = {
                        "body_part_id": selected_part.id,
                        "name": title[:120],
                        "what_it_checks": summary[:2000],
                        "prep_note": "Preparation varies by test. Follow the ordering clinician or laboratory instructions; do not change medicines without medical advice.",
                        "fasting_required": False,
                        "source_id": source.id,
                    }
                    if test is None:
                        db.add(BodyTest(sort_order=index, **test_values))
                    else:
                        for key, value in test_values.items():
                            setattr(test, key, value)
        await db.commit()
    await engine.dispose()
    return imported


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term", action="append", dest="terms", help="MedlinePlus search term; repeat for multiple terms")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(f"Imported {asyncio.run(import_topics(args.terms or list(DEFAULT_TERMS)))} MedlinePlus records")
