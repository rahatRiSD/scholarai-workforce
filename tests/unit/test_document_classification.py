from scholarai.domain.models.documents import DocumentType
from scholarai.infrastructure.documents.classification import classify_document


def test_classifies_transcript_by_content():
    assert classify_document("file1.pdf", "Official transcript. CGPA: 3.8. Semester 4.") == DocumentType.TRANSCRIPT


def test_classifies_financial_statement():
    text = "Financial aid application. Annual tuition and income."
    assert classify_document("form.pdf", text) == DocumentType.FINANCIAL_STATEMENT


def test_classifies_recommendation_letter():
    text = "I am pleased to recommend this student for the scholarship."
    assert classify_document("letter.pdf", text) == DocumentType.RECOMMENDATION_LETTER


def test_unknown_content_classified_as_other():
    assert classify_document("random.pdf", "Lorem ipsum dolor sit amet.") == DocumentType.OTHER


def test_filename_alone_can_drive_classification():
    assert classify_document("transcript_2024.pdf", "") == DocumentType.TRANSCRIPT
