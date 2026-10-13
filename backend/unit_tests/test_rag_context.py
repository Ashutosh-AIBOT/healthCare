from app.ai.chat_context import _score, _tokens
from app.tasks.document_tasks import _chunk_pages, _extract_report_values


def test_retrieval_score_prioritizes_title_matches() -> None:
    query = _tokens("high protein breakfast")
    assert _score(query, "High protein breakfast", "A practical meal") > _score(query, "Dinner ideas", "A practical meal")


def test_report_value_extraction_uses_source_text_only() -> None:
    values = _extract_report_values([(2, "Hemoglobin 13.2 g/dL reference 12.0-17.0")])
    assert values[0]["analyte_name"] == "Hemoglobin"
    assert values[0]["value_num"] == 13.2
    assert values[0]["page"] == 2


def test_report_chunks_keep_page_metadata() -> None:
    chunks = _chunk_pages([(1, "Glucose 98 mg/dL"), (2, "Vitamin D 24 ng/mL")])
    assert [(chunk[1], chunk[2]) for chunk in chunks] == [(1, "Glucose 98 mg/dL"), (2, "Vitamin D 24 ng/mL")]
