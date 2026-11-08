import os
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import fitz  # PyMuPDF
import docx

from backend.app.services.normalization_service import (
    normalize_extracted_text,
    EmptyDocumentError,
    normalize_whitespace
)

class DocumentParserError(Exception):
    pass

class UnsupportedFormatError(DocumentParserError):
    pass

class InsufficientTextError(DocumentParserError):
    pass

@dataclass
class ExtractedPage:
    page_number: int
    raw_text: str
    normalized_text: str
    char_count: int

@dataclass
class ParsedDocument:
    file_type: str
    page_count: int
    pages: List[ExtractedPage]
    full_text: str
    total_characters: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_ocr: bool = False

def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 checksum for document deduplication and integrity."""
    return hashlib.sha256(file_bytes).hexdigest()

def validate_file_signature(file_bytes: bytes, extension: str) -> bool:
    """
    Validates magic byte signatures to prevent executable and spoofed files.
    """
    ext = extension.lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"

    if ext == ".pdf":
        return file_bytes.startswith(b"%PDF")
    elif ext == ".docx":
        # DOCX is an OpenXML ZIP archive
        return file_bytes.startswith(b"PK\x03\x04")
    elif ext in [".txt", ".md"]:
        # Text files shouldn't have excessive null bytes
        sample = file_bytes[:1024]
        return b"\x00" not in sample
    return False

def get_mime_type_for_ext(extension: str) -> str:
    ext = extension.lower().replace(".", "")
    if ext == "pdf":
        return "application/pdf"
    elif ext == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext in ["txt", "md"]:
        return "text/plain"
    return "application/octet-stream"

# -------------------------------------------------------------------------
# Parser 1: PDF (PyMuPDF)
# -------------------------------------------------------------------------
class PDFParser:
    @staticmethod
    def parse(file_path: str) -> ParsedDocument:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise DocumentParserError(f"Corrupted or invalid PDF file: {str(e)}")

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            raise EmptyDocumentError("PDF document has 0 pages.")

        pages: List[ExtractedPage] = []
        total_extracted_chars = 0
        has_images_only = True

        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            raw_page_text = page.get_text("text")

            # Check if page has text
            if raw_page_text and raw_page_text.strip():
                try:
                    norm_text = normalize_extracted_text(raw_page_text)
                    has_images_only = False
                except EmptyDocumentError:
                    norm_text = ""
            else:
                norm_text = ""

            char_len = len(norm_text)
            total_extracted_chars += char_len

            pages.append(ExtractedPage(
                page_number=page_num,
                raw_text=raw_page_text or "",
                normalized_text=norm_text,
                char_count=char_len
            ))

        # Metadata extraction
        metadata = {
            "title": doc.metadata.get("title") or None,
            "author": doc.metadata.get("author") or None,
            "subject": doc.metadata.get("subject") or None,
            "creator": doc.metadata.get("creator") or None,
            "producer": doc.metadata.get("producer") or None,
            "format": doc.metadata.get("format") or "PDF",
            "page_count": page_count
        }
        doc.close()

        # Scanned page / OCR requirement detection
        # If total extracted text is negligible (< 40 characters across multi-page or 0 text)
        if total_extracted_chars < 40:
            raise InsufficientTextError(
                f"Document appears to contain scanned images without extractable digital text (only {total_extracted_chars} characters extracted across {page_count} page(s)). OCR is required."
            )

        full_text = "\n\n".join(p.normalized_text for p in pages if p.normalized_text)
        return ParsedDocument(
            file_type="pdf",
            page_count=page_count,
            pages=pages,
            full_text=full_text,
            total_characters=total_extracted_chars,
            metadata=metadata,
            requires_ocr=False
        )

# -------------------------------------------------------------------------
# Parser 2: DOCX (python-docx)
# -------------------------------------------------------------------------
class DOCXParser:
    @staticmethod
    def parse(file_path: str, words_per_page: int = 350) -> ParsedDocument:
        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise DocumentParserError(f"Corrupted or invalid DOCX document: {str(e)}")

        sections_text: List[str] = []

        # 1. Paragraphs with heading markup
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            if p.style and p.style.name.startswith("Heading"):
                # Preserve heading hierarchy
                sections_text.append(f"## {text}")
            else:
                sections_text.append(text)

        # 2. Tables
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells if cell.text.strip()]
                if row_cells:
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                sections_text.append("\n".join(table_rows))

        raw_full_text = "\n\n".join(sections_text)
        if not raw_full_text.strip():
            raise EmptyDocumentError("DOCX document contains no text content.")

        norm_full_text = normalize_extracted_text(raw_full_text)

        # Logical page partitioning preserving natural section breaks
        words = norm_full_text.split()
        total_words = len(words)
        page_count = max(1, (total_words + words_per_page - 1) // words_per_page)

        pages: List[ExtractedPage] = []
        for p_idx in range(page_count):
            page_num = p_idx + 1
            start_w = p_idx * words_per_page
            end_w = min(start_w + words_per_page, total_words)
            page_words = words[start_w:end_w]
            page_str = " ".join(page_words)

            pages.append(ExtractedPage(
                page_number=page_num,
                raw_text=page_str,
                normalized_text=page_str,
                char_count=len(page_str)
            ))

        # Metadata
        core_props = doc.core_properties
        metadata = {
            "title": getattr(core_props, "title", None) or None,
            "author": getattr(core_props, "author", None) or None,
            "category": getattr(core_props, "category", None) or None,
            "comments": getattr(core_props, "comments", None) or None,
            "page_count": page_count
        }

        return ParsedDocument(
            file_type="docx",
            page_count=page_count,
            pages=pages,
            full_text=norm_full_text,
            total_characters=len(norm_full_text),
            metadata=metadata,
            requires_ocr=False
        )

# -------------------------------------------------------------------------
# Parser 3: TXT
# -------------------------------------------------------------------------
class TXTParser:
    @staticmethod
    def parse(file_path: str, lines_per_page: int = 45) -> ParsedDocument:
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content: Optional[str] = None

        for enc in encodings_to_try:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            # Fallback with replacement characters
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        if not content or not content.strip():
            raise EmptyDocumentError("TXT document contains no readable text content.")

        norm_full_text = normalize_extracted_text(content)
        lines = norm_full_text.split("\n")
        total_lines = len(lines)
        page_count = max(1, (total_lines + lines_per_page - 1) // lines_per_page)

        pages: List[ExtractedPage] = []
        for p_idx in range(page_count):
            page_num = p_idx + 1
            start_l = p_idx * lines_per_page
            end_l = min(start_l + lines_per_page, total_lines)
            page_str = "\n".join(lines[start_l:end_l]).strip()

            pages.append(ExtractedPage(
                page_number=page_num,
                raw_text=page_str,
                normalized_text=page_str,
                char_count=len(page_str)
            ))

        metadata = {
            "format": "Plain Text",
            "line_count": total_lines,
            "page_count": page_count
        }

        return ParsedDocument(
            file_type="txt",
            page_count=page_count,
            pages=pages,
            full_text=norm_full_text,
            total_characters=len(norm_full_text),
            metadata=metadata,
            requires_ocr=False
        )

# -------------------------------------------------------------------------
# Main Parser Dispatcher
# -------------------------------------------------------------------------
def parse_document(file_path: str, file_extension: str) -> ParsedDocument:
    """Dispatches document to format-specific parser based on extension."""
    ext = file_extension.lower().replace(".", "").strip()
    if ext == "pdf":
        return PDFParser.parse(file_path)
    elif ext in ["docx", "doc"]:
        return DOCXParser.parse(file_path)
    elif ext in ["txt", "md"]:
        return TXTParser.parse(file_path)
    else:
        raise UnsupportedFormatError(f"Unsupported file format: '.{ext}'. Supported formats: PDF, DOCX, TXT.")
