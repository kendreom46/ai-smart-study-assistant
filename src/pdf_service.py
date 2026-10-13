"""
PDF Processing Service for StudyMate AI
Handles robust text extraction from PDF files using PyMuPDF (fitz).
Includes safety validations, scanned document detection, and length management.
"""

from typing import Any, Dict, List, Optional
import io

# PyMuPDF is imported as fitz
try:
    import fitz  # type: ignore
except ImportError:
    fitz = None

# 15 MB file size limit for academic uploads
MAX_PDF_SIZE_BYTES = 15 * 1024 * 1024
MAX_PAGE_LIMIT = 100
MAX_CHUNK_CHARS = 10000


def validate_pdf_size(file_bytes: bytes, max_size_bytes: int = MAX_PDF_SIZE_BYTES) -> Optional[str]:
    """Validate that the uploaded file does not exceed size limitations."""
    if not file_bytes:
        return "The uploaded file is empty (0 bytes)."
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = len(file_bytes) / (1024 * 1024)
        return f"File size ({actual_mb:.1f} MB) exceeds maximum permitted size of {max_mb:.0f} MB."
    return None


def extract_text_from_pdf(
    file_bytes: bytes,
    max_pages: int = MAX_PAGE_LIMIT,
) -> Dict[str, Any]:
    """
    Extract readable text from a PDF byte stream safely using PyMuPDF.

    Returns a dictionary:
    {
        "success": bool,
        "text": str,
        "total_pages": int,
        "processed_pages": int,
        "is_scanned": bool,
        "is_encrypted": bool,
        "error": str | None,
        "warning": str | None,
        "pages": List[str]
    }
    """
    if fitz is None:
        return {
            "success": False,
            "text": "",
            "total_pages": 0,
            "processed_pages": 0,
            "is_scanned": False,
            "is_encrypted": False,
            "error": "PyMuPDF library is not available in the current environment.",
            "warning": None,
            "pages": [],
        }

    # Size check
    size_error = validate_pdf_size(file_bytes)
    if size_error:
        return {
            "success": False,
            "text": "",
            "total_pages": 0,
            "processed_pages": 0,
            "is_scanned": False,
            "is_encrypted": False,
            "error": size_error,
            "warning": None,
            "pages": [],
        }

    # Header signature check
    if not file_bytes.startswith(b"%PDF-"):
        return {
            "success": False,
            "text": "",
            "total_pages": 0,
            "processed_pages": 0,
            "is_scanned": False,
            "is_encrypted": False,
            "error": "Invalid PDF format: File header does not match PDF signature.",
            "warning": None,
            "pages": [],
        }

    doc = None
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # Check encryption
        if doc.is_encrypted:
            return {
                "success": False,
                "text": "",
                "total_pages": len(doc),
                "processed_pages": 0,
                "is_scanned": False,
                "is_encrypted": True,
                "error": "This PDF is password-protected or encrypted. Please remove encryption before uploading.",
                "warning": None,
                "pages": [],
            }

        total_pages = len(doc)
        if total_pages == 0:
            return {
                "success": False,
                "text": "",
                "total_pages": 0,
                "processed_pages": 0,
                "is_scanned": False,
                "is_encrypted": False,
                "error": "The PDF document contains 0 pages.",
                "warning": None,
                "pages": [],
            }

        pages_to_process = min(total_pages, max_pages)
        page_texts: List[str] = []
        total_extracted_chars = 0

        for page_idx in range(pages_to_process):
            page = doc.load_page(page_idx)
            page_text = page.get_text("text").strip()
            page_texts.append(page_text)
            total_extracted_chars += len(page_text)

        full_text = "\n\n".join(
            f"--- [Page {idx + 1}] ---\n{t}"
            for idx, t in enumerate(page_texts)
            if t
        ).strip()

        # Check for scanned or image-only documents
        is_scanned = total_extracted_chars < 50
        warning = None

        if is_scanned:
            warning = (
                "Notice: This PDF contains little or no machine-readable text. "
                "It is likely a scanned document or consists solely of images. "
                "Optical Character Recognition (OCR) is not enabled in this version. "
                "Please upload a text-searchable digital PDF."
            )
        elif total_pages > max_pages:
            warning = (
                f"Notice: This document contains {total_pages} pages. "
                f"To maintain fast processing and stay within model context limits, "
                f"only the first {max_pages} pages were processed."
            )

        return {
            "success": not is_scanned,
            "text": full_text,
            "total_pages": total_pages,
            "processed_pages": pages_to_process,
            "is_scanned": is_scanned,
            "is_encrypted": False,
            "error": None if not is_scanned else warning,
            "warning": warning,
            "pages": page_texts,
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "total_pages": 0,
            "processed_pages": 0,
            "is_scanned": False,
            "is_encrypted": False,
            "error": f"Failed to parse PDF: {str(e)}",
            "warning": None,
            "pages": [],
        }
    finally:
        if doc is not None:
            doc.close()


def chunk_text(text: str, max_chunk_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """
    Split extracted document text into logical chunks for downstream processing.
    Splits along double newlines or sentences to preserve paragraph structure.
    """
    if not text or len(text) <= max_chunk_chars:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len + 2 > max_chunk_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            if para_len > max_chunk_chars:
                # Force chunk exceptionally huge individual paragraphs
                for i in range(0, para_len, max_chunk_chars):
                    chunks.append(para[i : i + max_chunk_chars])
                continue
        current_chunk.append(para)
        current_len += para_len + 2

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks
