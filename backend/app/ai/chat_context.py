"""Scoped, citation-producing retrieval context for Xomni chat."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.documents import DocumentChunk, LabReportValue
from app.models.family_member import FamilyMember
from app.models.learn import BodyTest, LearnItem
from app.models.rag_context import UserPersonalContext


@dataclass
class RetrievedSource:
    source: str
    source_id: str
    label: str
    page: int | None = None
    score: int = 0
    content: str = ""

    def citation(self) -> dict:
        result = {"source": self.source, "source_id": self.source_id, "label": self.label}
        if self.page is not None:
            result["page"] = self.page
        return result


@dataclass
class ChatContext:
    text: str
    citations: list[dict]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _score(question: set[str], title: str, content: str) -> int:
    title_tokens = _tokens(title)
    content_tokens = _tokens(content)
    return len(question & content_tokens) + (2 * len(question & title_tokens))


async def build_chat_context(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID | None,
    question: str,
    member_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
) -> ChatContext:
    """Retrieve global knowledge plus only the user's permitted report context."""
    question_tokens = _tokens(question)
    sources: list[RetrievedSource] = []

    learn_rows = list((await db.execute(
        select(LearnItem).options(selectinload(LearnItem.category)).limit(300)
    )).scalars().all())
    for item in learn_rows:
        category = item.category.title if item.category else "Learn"
        content = "\n".join(filter(None, [item.summary, item.content, item.healthy_role]))
        score = _score(question_tokens, f"{item.title} {category}", content)
        if score:
            sources.append(RetrievedSource("learn", str(item.id), item.title, score=score, content=content[:1200]))

    test_rows = list((await db.execute(select(BodyTest).options(selectinload(BodyTest.body_part)).limit(300))).scalars().all())
    for test in test_rows:
        body_part = test.body_part.name if test.body_part else "Health test"
        content = "\n".join(filter(None, [test.what_it_checks, test.prep_note]))
        score = _score(question_tokens, f"{test.name} {body_part}", content)
        if score:
            sources.append(RetrievedSource("test_info", str(test.id), test.name, score=score, content=content[:1200]))

    context_row = await db.scalar(select(UserPersonalContext).where(UserPersonalContext.user_id == user_id))
    if context_row and context_row.context_json:
        personal_text = "\n".join(
            f"{key.replace('_', ' ').title()}: {value}"
            for key, value in context_row.context_json.items()
            if value not in (None, "", [], {})
        )
        personal_score = _score(question_tokens, "personal preferences and habits", personal_text)
        if personal_score or question_tokens:
            sources.append(RetrievedSource("personal_context", str(context_row.id), "Your confirmed preferences", score=max(1, personal_score), content=personal_text[:1800]))

    if family_id is not None:
        member_query = select(FamilyMember.id).where(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id,
            FamilyMember.deleted_at.is_(None),
        )
        permitted_member_ids = set((await db.execute(member_query)).scalars().all())
        if member_id is not None:
            permitted_member_ids &= {member_id}
        if permitted_member_ids:
            chunk_query = select(DocumentChunk).where(DocumentChunk.member_id.in_(permitted_member_ids))
            value_query = select(LabReportValue).where(LabReportValue.member_id.in_(permitted_member_ids))
            if document_id is not None:
                chunk_query = chunk_query.where(DocumentChunk.document_id == document_id)
                value_query = value_query.where(LabReportValue.document_id == document_id)
            chunks = list((await db.execute(chunk_query)).scalars().all())
            values = list((await db.execute(value_query)).scalars().all())
            for chunk in chunks:
                score = _score(question_tokens, "lab report", chunk.content)
                sources.append(RetrievedSource("report_chunk", str(chunk.document_id), f"Report page {chunk.page or '?'}", chunk.page, score or 1, chunk.content[:1600]))
            for value in values:
                value_text = f"{value.analyte_name} {value.analyte_code} {value.value_num or value.value_text or ''} {value.unit or ''} reference {value.ref_low or ''} to {value.ref_high or ''} flag {value.flag or ''}"
                score = _score(question_tokens, value.analyte_name, value_text)
                sources.append(RetrievedSource("report_value", str(value.document_id), value.analyte_name, value.page, score or 1, value_text))

    sources.sort(key=lambda item: item.score, reverse=True)
    selected = sources[:10]
    if not selected:
        return ChatContext("No matching Learn or personal report context was found.", [])

    sections = []
    for item in selected:
        sections.append(f"[{item.source}:{item.label}]\n{item.content}")
    return ChatContext("\n\n".join(sections)[:12000], [item.citation() for item in selected])
