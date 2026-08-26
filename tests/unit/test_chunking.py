from scholarai.infrastructure.rag.chunking import chunk_document

DOCUMENT = """# Scholarship Policy

## 1. Overview
This policy governs scholarship awards.

## 2. Eligibility
### 2.1 Academic Requirements
Minimum CGPA is 3.75. Students must have completed at least 30 credits.

### 2.2 Standing
Students must be in good academic standing with no more than one failed course.
"""


def test_chunk_document_tracks_section_headings():
    chunks = chunk_document(DOCUMENT)
    sections = [c.section for c in chunks]
    assert "1. Overview" in sections
    assert "2.1 Academic Requirements" in sections
    assert "2.2 Standing" in sections


def test_chunk_document_indexes_sequentially():
    chunks = chunk_document(DOCUMENT)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_empty_document_produces_no_chunks():
    assert chunk_document("") == []


def test_short_document_still_produces_one_chunk():
    chunks = chunk_document("A short policy statement with no headings at all here.")
    assert len(chunks) == 1
