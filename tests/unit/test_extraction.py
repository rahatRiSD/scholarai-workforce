from scholarai.domain.models.documents import Document, DocumentType
from scholarai.infrastructure.documents.extraction import build_extracted_data, extract_from_text

TRANSCRIPT = """
ACADEMIC TRANSCRIPT
Student Name: Test Student
Student ID: STU-9001
Program: BSc Computer Science
Current Semester: 5
CGPA: 3.85
Credits Completed: 78
Expected Graduation Year: 2027

Semester 1 GPA: 3.60
Semester 2 GPA: 3.95

Achievements:
- [award] Dean's List (2024)
- [competition] Coding Contest Finalist (2023)
"""

FINANCIAL = """
FINANCIAL AID APPLICATION FORM
Annual Family Income: $32,000
Household Size: 5
Dependents: 3
Annual Tuition: $12,000
Current Aid: $1,000
"""


def test_extract_from_text_finds_core_fields():
    fields = extract_from_text("transcript.txt", TRANSCRIPT)
    assert fields["student_id"] == "STU-9001"
    assert fields["cgpa"] == 3.85
    assert fields["credits_completed"] == 78
    assert fields["semester_gpas"] == (3.60, 3.95)
    assert len(fields["achievements"]) == 2


def test_extract_from_text_parses_money_fields():
    fields = extract_from_text("financial.txt", FINANCIAL)
    assert fields["family_income_annual"] == 32000.0
    assert fields["household_size"] == 5
    assert fields["tuition_cost_annual"] == 12000.0


def test_build_extracted_data_merges_across_documents():
    docs = [
        Document(
            filename="transcript.txt",
            document_type=DocumentType.TRANSCRIPT,
            raw_text=TRANSCRIPT,
            readable=True,
            page_count=1,
        ),
        Document(
            filename="financial.txt",
            document_type=DocumentType.FINANCIAL_STATEMENT,
            raw_text=FINANCIAL,
            readable=True,
            page_count=1,
        ),
    ]
    data = build_extracted_data(docs)
    assert data.cgpa == 3.85
    assert data.family_income_annual == 32000.0
    assert not data.documents_missing
    assert DocumentType.TRANSCRIPT in data.documents_present


def test_build_extracted_data_flags_missing_transcript():
    docs = [
        Document(
            filename="financial.txt",
            document_type=DocumentType.FINANCIAL_STATEMENT,
            raw_text=FINANCIAL,
            readable=True,
            page_count=1,
        ),
    ]
    data = build_extracted_data(docs)
    assert "transcript" in data.documents_missing


def test_build_extracted_data_reports_unreadable_documents():
    docs = [Document(filename="bad.txt", document_type=DocumentType.UNREADABLE, raw_text="", readable=False)]
    data = build_extracted_data(docs)
    assert data.unreadable_documents == ("bad.txt",)
