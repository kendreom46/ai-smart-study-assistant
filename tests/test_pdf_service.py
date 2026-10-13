"""
Unit tests for StudyMate AI PDF text extraction and error handling.
Tests run completely locally without needing external APIs.
"""

import pytest
from src.pdf_service import (
    validate_pdf_size,
    extract_text_from_pdf,
    chunk_text,
    MAX_PDF_SIZE_BYTES,
)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def create_dummy_pdf_bytes(text: str = "Hello StudyMate AI", num_pages: int = 1) -> bytes:
    """Helper to generate an in-memory valid PDF for testing."""
    if fitz is None:
        # Fallback raw minimal PDF bytes if fitz is not yet imported
        return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    doc = fitz.open()
    for _ in range(num_pages):
        page = doc.new_page()
        if text:
            page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_validate_pdf_size_empty():
    """Verify that empty 0-byte files return a clean error message."""
    error = validate_pdf_size(b"")
    assert error is not None
    assert "empty" in error.lower()


def test_validate_pdf_size_too_large():
    """Verify that files exceeding the maximum size limit are rejected."""
    oversized_bytes = b"0" * (MAX_PDF_SIZE_BYTES + 1024)
    error = validate_pdf_size(oversized_bytes)
    assert error is not None
    assert "exceeds maximum permitted size" in error


def test_extract_invalid_pdf_header():
    """Verify that files lacking the %PDF- header are rejected safely."""
    fake_pdf = b"NOT_A_PDF_FILE_HEADER_DATA"
    result = extract_text_from_pdf(fake_pdf)
    assert result["success"] is False
    assert "Invalid PDF format" in result["error"]


@pytest.mark.skipif(fitz is None, reason="PyMuPDF not installed in global runner")
def test_extract_valid_pdf_text():
    """Verify that real text is extracted accurately from a valid PDF."""
    content = "Operating Systems: CPU Scheduling and Memory Management."
    pdf_bytes = create_dummy_pdf_bytes(content, num_pages=2)

    result = extract_text_from_pdf(pdf_bytes)
    assert result["success"] is True
    assert result["total_pages"] == 2
    assert "CPU Scheduling" in result["text"]
    assert result["is_scanned"] is False
    assert result["error"] is None


@pytest.mark.skipif(fitz is None, reason="PyMuPDF not installed in global runner")
def test_scanned_pdf_detection():
    """Verify that PDFs with no text (e.g., scanned images) trigger warning."""
    # Blank PDF with no text inserted
    pdf_bytes = create_dummy_pdf_bytes(text="", num_pages=1)
    result = extract_text_from_pdf(pdf_bytes)
    assert result["is_scanned"] is True
    assert "scanned document" in result["warning"].lower()


def test_chunk_text_utility():
    """Verify that chunk_text splits long text into coherent segments."""
    sample_text = "\n\n".join([f"Paragraph {i}: Academic notes on topic." for i in range(50)])
    chunks = chunk_text(sample_text, max_chunk_chars=200)

    assert len(chunks) > 1
    # Check that each chunk is within limits
    for chunk in chunks:
        assert len(chunk) <= 250  # with formatting boundary
