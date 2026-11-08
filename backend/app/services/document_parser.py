import os
import hashlib
from typing import List, Dict, Any, Tuple
import fitz  # PyMuPDF
import docx

def compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def extract_pdf_chunks(file_path: str, chunk_size: int = 800, overlap: int = 100) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Extracts text from PDF file preserving exact page numbers.
    Each chunk is strictly attributed to its page number.
    """
    doc = fitz.open(file_path)
    page_count = len(doc)
    all_chunks = []
    chunk_index = 0

    for page_num in range(1, page_count + 1):
        page = doc[page_num - 1]
        text = page.get_text("text").strip()
        if not text:
            continue

        # Split page text into overlapping windows if too large, or keep page intact
        if len(text) <= chunk_size + 200:
            all_chunks.append({
                "page_number": page_num,
                "chunk_index": chunk_index,
                "text_content": text,
                "char_start": 0,
                "char_end": len(text)
            })
            chunk_index += 1
        else:
            # Sliding window within page
            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                # Adjust end to nearest whitespace if possible
                if end < len(text):
                    space_pos = text.rfind(" ", start, end)
                    if space_pos > start + 200:
                        end = space_pos

                chunk_text = text[start:end].strip()
                if chunk_text:
                    all_chunks.append({
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                        "text_content": chunk_text,
                        "char_start": start,
                        "char_end": end
                    })
                    chunk_index += 1

                if end >= len(text):
                    break
                start = max(start + 1, end - overlap)

    doc.close()
    return page_count, all_chunks

def extract_docx_chunks(file_path: str, words_per_page: int = 400) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Extracts text from DOCX file. Estimates page numbers based on word density / explicit page breaks.
    """
    doc = docx.Document(file_path)
    paragraphs = []
    for p in doc.paragraphs:
        if p.text.strip():
            paragraphs.append(p.text.strip())
    
    # Also extract table text
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)

    full_text = "\n\n".join(paragraphs)
    words = full_text.split()
    total_words = len(words)
    estimated_pages = max(1, (total_words + words_per_page - 1) // words_per_page)

    all_chunks = []
    chunk_index = 0

    for p_idx in range(estimated_pages):
        page_num = p_idx + 1
        start_w = p_idx * words_per_page
        end_w = min(start_w + words_per_page, total_words)
        page_words = words[start_w:end_w]
        page_text = " ".join(page_words)

        if page_text:
            all_chunks.append({
                "page_number": page_num,
                "chunk_index": chunk_index,
                "text_content": page_text,
                "char_start": start_w,
                "char_end": end_w
            })
            chunk_index += 1

    return estimated_pages, all_chunks

def extract_txt_chunks(file_path: str, lines_per_page: int = 40) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Extracts text from TXT files. Groups lines into logical pages.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    clean_lines = [line.rstrip() for line in lines]
    total_lines = len(clean_lines)
    estimated_pages = max(1, (total_lines + lines_per_page - 1) // lines_per_page)

    all_chunks = []
    chunk_index = 0

    for p_idx in range(estimated_pages):
        page_num = p_idx + 1
        start_l = p_idx * lines_per_page
        end_l = min(start_l + lines_per_page, total_lines)
        page_text = "\n".join(clean_lines[start_l:end_l]).strip()

        if page_text:
            all_chunks.append({
                "page_number": page_num,
                "chunk_index": chunk_index,
                "text_content": page_text,
                "char_start": start_l,
                "char_end": end_l
            })
            chunk_index += 1

    return estimated_pages, all_chunks

def process_document(file_path: str, file_type: str) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Generic dispatcher based on file extension.
    Returns (page_count, chunks_list).
    """
    ext = file_type.lower().replace(".", "")
    if ext == "pdf":
        return extract_pdf_chunks(file_path)
    elif ext in ["docx", "doc"]:
        return extract_docx_chunks(file_path)
    elif ext in ["txt", "md"]:
        return extract_txt_chunks(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
