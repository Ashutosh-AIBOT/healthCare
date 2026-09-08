"""Keyword-overlap RAG skeleton with LLM gateway integration."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway, Provider, LLMResponse
from app.models.documents import DocumentChunk, LabReportValue


@dataclass
class Citation:
    source: str  # "lab_value" | "chunk"
    document_id: uuid.UUID
    page: int | None
    label: str


@dataclass
class RagAnswer:
    text: str
    citations: list[Citation]


def fake_embedding(text: str, dims: int = 8) -> list[float]:
    """Deterministic placeholder vector for skeleton storage."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    vec = [0.0] * dims
    for i, tok in enumerate(tokens):
        vec[i % dims] += (sum(ord(c) for c in tok) % 97) / 97.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [round(v / norm, 6) for v in vec]


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


async def retrieve_chunks(
    db: AsyncSession,
    *,
    member_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
    limit: int = 5,
) -> list[DocumentChunk]:
    """Pre-filter by member_id; score by simple keyword overlap."""
    q = select(DocumentChunk).where(DocumentChunk.member_id == member_id)
    if document_id is not None:
        q = q.where(DocumentChunk.document_id == document_id)
    rows = list((await db.execute(q)).scalars().all())
    q_tokens = _tokenize(question)
    if not q_tokens:
        return rows[:limit]

    scored: list[tuple[int, DocumentChunk]] = []
    for chunk in rows:
        overlap = len(q_tokens & _tokenize(chunk.content))
        if overlap > 0:
            scored.append((overlap, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored:
        return [c for _, c in scored[:limit]]
    return rows[:limit]


async def build_cited_answer(
    db: AsyncSession,
    *,
    member_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
    llm_gateway: LLMGateway | None = None,
) -> RagAnswer:
    """Compose a cited answer from lab_report_values + overlapping chunks.

    Uses the LLM gateway for generation if available, falling back to
    keyword-overlap template generation.
    """
    lv_q = select(LabReportValue).where(LabReportValue.member_id == member_id)
    if document_id is not None:
        lv_q = lv_q.where(LabReportValue.document_id == document_id)
    values = list((await db.execute(lv_q)).scalars().all())

    chunks = await retrieve_chunks(
        db, member_id=member_id, question=question, document_id=document_id
    )

    q_tokens = _tokenize(question)
    relevant_values = [
        v
        for v in values
        if q_tokens & _tokenize(f"{v.analyte_name} {v.analyte_code} {v.unit or ''}")
    ]
    if not relevant_values:
        relevant_values = values

    parts: list[str] = []
    citations: list[Citation] = []

    if relevant_values:
        parts.append("Based on values extracted from your lab report:")
        for v in relevant_values:
            num = f"{v.value_num}" if v.value_num is not None else (v.value_text or "—")
            unit = f" {v.unit}" if v.unit else ""
            page_note = f" (page {v.page})" if v.page else ""
            parts.append(f"- {v.analyte_name}: {num}{unit}{page_note}")
            citations.append(
                Citation(
                    source="lab_value",
                    document_id=v.document_id,
                    page=v.page,
                    label=v.analyte_name,
                )
            )
    elif chunks:
        parts.append("From your report text:")
        for c in chunks[:3]:
            snippet = c.content[:240].strip()
            page_note = f" (page {c.page})" if c.page else ""
            parts.append(f"- {snippet}{page_note}")
            citations.append(
                Citation(
                    source="chunk",
                    document_id=c.document_id,
                    page=c.page,
                    label=f"chunk-{c.chunk_index}",
                )
            )
    else:
        parts.append(
            "I could not find this in your reports. "
            "Upload a lab report for this member, then ask again."
        )

    # Use LLM gateway for generation if available
    if llm_gateway is not None:
        try:
            # Build a context string from the retrieved information
            context = "\n".join(parts) if parts else question

            llm_result: LLMResponse = await llm_gateway.complete(
                prompt=f"""You are a helpful health assistant. Based on the following context from a lab report, provide a clear explanation of the user's question.

Context:
{context}

Question: {question}

Instructions:
- Provide a helpful, informative response based ONLY on the context above
- Do NOT provide any diagnosis, dosage, prognosis, or treatment advice
- Include a medical disclaimer at the end
- If the context doesn't contain enough information, state that clearly
- Reference specific values by name when possible

Response:""",
                model="nvidia/nemotron-3.5-lightning-30b-a3b"
            )

            # Append the medical disclaimer
            disclaimer = "These figures are explanations of what appears on the report, not a clinical interpretation. Discuss them with a qualified doctor."
            full_text = llm_result.text + "\n\n" + disclaimer if not llm_result.text.endswith(disclaimer) else llm_result.text

            # Convert LLMResponse citations to Citation dataclasses if needed
            llm_citations = llm_result.citations or []
            converted_citations: list[Citation] = []
            for c in llm_citations:
                if isinstance(c, Citation):
                    converted_citations.append(c)
                elif isinstance(c, dict):
                    converted_citations.append(
                        Citation(
                            source=c.get("source", "chunk"),
                            document_id=uuid.UUID(c.get("document_id", str(uuid.UUID(int=0)))),
                            page=c.get("page"),
                            label=c.get("label", ""),
                        )
                    )

            return RagAnswer(
                text=full_text,
                citations=converted_citations,
            )
        except Exception:
            # Fall back to template generation on error
            pass

    # Fallback: template-based answer (original behavior)
    parts.append(
        "These figures are explanations of what appears on the report, "
        "not a clinical interpretation. Discuss them with a qualified doctor."
    )
    return RagAnswer(text="\n".join(parts), citations=citations)