"""Unit tests for DocumentParser text extraction service."""

import io
import zipfile

import pytest
from backend.app.services.document_parser import (
    MAX_FILE_BYTES,
    DocumentParser,
    DocumentParsingError,
)


def create_synthetic_docx(text: str) -> bytes:
    """Create a minimal valid DOCX file in memory containing the given text."""
    xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t>{text}</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", xml_content)
    return buf.getvalue()


def create_synthetic_pdf(text: str) -> bytes:
    """Create a minimal valid PDF file in memory using pypdf."""
    from pypdf import PageObject, PdfWriter

    writer = PdfWriter()
    # Add a blank page with metadata
    page = PageObject.create_blank_page(width=72, height=72)
    writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_parse_plain_text():
    parser = DocumentParser()
    raw = b"System Requirements Specification\n\n1. User Authentication\n2. Real-time Scheduling"
    doc = parser.parse_document("specs.txt", raw)
    assert doc.filename == "specs.txt"
    assert doc.file_type == "text"
    assert "User Authentication" in doc.content
    assert doc.character_count > 0


def test_parse_markdown():
    parser = DocumentParser()
    raw = b"# Project Overview\n\n- Milestone 1: MVP\n- Milestone 2: Hardening"
    doc = parser.parse_document("README.md", raw)
    assert doc.filename == "README.md"
    assert doc.file_type == "text"
    assert "Milestone 1: MVP" in doc.content


def test_parse_docx():
    parser = DocumentParser()
    docx_bytes = create_synthetic_docx("Cloud Native Architecture and Resilience Spec")
    doc = parser.parse_document("architecture.docx", docx_bytes)
    assert doc.filename == "architecture.docx"
    assert doc.file_type == "docx"
    assert doc.content == "Cloud Native Architecture and Resilience Spec"


def test_parse_pdf():
    parser = DocumentParser()
    pdf_bytes = create_synthetic_pdf("Sample Project Plan")
    doc = parser.parse_document("requirements.pdf", pdf_bytes)
    assert doc.filename == "requirements.pdf"
    assert doc.file_type == "pdf"


def test_unsupported_format_raises():
    parser = DocumentParser()
    with pytest.raises(DocumentParsingError, match="Unsupported document format"):
        parser.parse_document("script.exe", b"\x4d\x5a")


def test_file_size_limit_raises():
    parser = DocumentParser()
    large_payload = b"X" * (MAX_FILE_BYTES + 1024)
    with pytest.raises(DocumentParsingError, match="exceeds maximum allowable size"):
        parser.parse_document("huge.txt", large_payload)


def test_parse_multiple_and_format_for_prompt():
    parser = DocumentParser()
    files = [
        ("reqs.txt", b"Requirement 1: Security audit"),
        ("spec.md", b"# Architecture: Event-driven"),
    ]
    docs = parser.parse_multiple(files)
    assert len(docs) == 2
    prompt_snippet = parser.format_for_prompt(docs)
    assert "=== ATTACHED SPEC: reqs.txt" in prompt_snippet
    assert "Security audit" in prompt_snippet
    assert "Event-driven" in prompt_snippet
