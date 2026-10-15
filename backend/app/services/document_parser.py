"""Document parser for extracting text from project requirements and specifications."""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit per file
MAX_EXTRACTED_CHARS_PER_DOC = 30_000
MAX_TOTAL_CHARS = 80_000


@dataclass
class ExtractedDocument:
    filename: str
    file_type: str
    content: str
    character_count: int


class DocumentParsingError(ValueError):
    """Raised when an uploaded document cannot be parsed or exceeds limits."""

    pass


class DocumentParser:
    """Extracts and sanitizes text from supported document types (.txt, .md, .docx, .pdf)."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Strip null bytes, normalize linebreaks and excessive whitespace."""
        text = text.replace("\x00", "")
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def parse_plain_text(self, filename: str, raw_bytes: bytes) -> ExtractedDocument:
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1", errors="replace")

        content = self.sanitize_text(content)
        truncated = content[:MAX_EXTRACTED_CHARS_PER_DOC]
        return ExtractedDocument(
            filename=filename,
            file_type="text",
            content=truncated,
            character_count=len(truncated),
        )

    def parse_docx(self, filename: str, raw_bytes: bytes) -> ExtractedDocument:
        try:
            with io.BytesIO(raw_bytes) as docx_file, zipfile.ZipFile(docx_file) as zf:
                if "word/document.xml" not in zf.namelist():
                    raise DocumentParsingError(f"'{filename}' is not a valid DOCX file.")
                xml_content = zf.read("word/document.xml")

            tree = ET.fromstring(xml_content)
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.findall(".//w:p", namespaces):
                texts = [node.text for node in p.findall(".//w:t", namespaces) if node.text]
                if texts:
                    paragraphs.append("".join(texts))

            raw_text = "\n".join(paragraphs)
            content = self.sanitize_text(raw_text)
            truncated = content[:MAX_EXTRACTED_CHARS_PER_DOC]
            return ExtractedDocument(
                filename=filename,
                file_type="docx",
                content=truncated,
                character_count=len(truncated),
            )
        except Exception as exc:
            if isinstance(exc, DocumentParsingError):
                raise
            raise DocumentParsingError(f"Failed to parse DOCX file '{filename}': {exc}") from exc

    def parse_pdf(self, filename: str, raw_bytes: bytes) -> ExtractedDocument:
        try:
            from pypdf import PdfReader

            with io.BytesIO(raw_bytes) as pdf_file:
                reader = PdfReader(pdf_file)
                page_texts = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        page_texts.append(f"--- Page {i + 1} ---\n{text.strip()}")

                raw_text = "\n\n".join(page_texts)
                content = self.sanitize_text(raw_text)
                truncated = content[:MAX_EXTRACTED_CHARS_PER_DOC]
                return ExtractedDocument(
                    filename=filename,
                    file_type="pdf",
                    content=truncated,
                    character_count=len(truncated),
                )
        except Exception as exc:
            raise DocumentParsingError(f"Failed to parse PDF file '{filename}': {exc}") from exc

    def parse_document(self, filename: str, raw_bytes: bytes) -> ExtractedDocument:
        if len(raw_bytes) > MAX_FILE_BYTES:
            raise DocumentParsingError(
                f"File '{filename}' exceeds maximum allowable size of "
                f"{MAX_FILE_BYTES // (1024 * 1024)}MB."
            )

        suffix = Path(filename).suffix.lower()
        if suffix in (".txt", ".md", ".markdown"):
            return self.parse_plain_text(filename, raw_bytes)
        elif suffix == ".docx":
            return self.parse_docx(filename, raw_bytes)
        elif suffix == ".pdf":
            return self.parse_pdf(filename, raw_bytes)
        else:
            raise DocumentParsingError(
                f"Unsupported document format '{suffix}'. Supported: .txt, .md, .docx, .pdf"
            )

    def parse_multiple(self, files: list[tuple[str, bytes]]) -> list[ExtractedDocument]:
        extracted: list[ExtractedDocument] = []
        total_chars = 0

        for filename, content_bytes in files:
            doc = self.parse_document(filename, content_bytes)
            if total_chars + doc.character_count > MAX_TOTAL_CHARS:
                allowed = max(0, MAX_TOTAL_CHARS - total_chars)
                if allowed > 0:
                    doc = ExtractedDocument(
                        filename=doc.filename,
                        file_type=doc.file_type,
                        content=doc.content[:allowed],
                        character_count=allowed,
                    )
                    extracted.append(doc)
                break
            extracted.append(doc)
            total_chars += doc.character_count

        return extracted

    @staticmethod
    def format_for_prompt(docs: list[ExtractedDocument]) -> str:
        if not docs:
            return ""
        sections = []
        for doc in docs:
            sections.append(
                f"=== ATTACHED SPEC: {doc.filename} ({doc.file_type}) ===\n{doc.content}\n"
            )
        return "\n".join(sections)
