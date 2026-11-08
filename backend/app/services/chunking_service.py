import re
from typing import List, Dict, Any
from dataclasses import dataclass
from backend.app.services.document_parser import ParsedDocument, ExtractedPage

@dataclass
class ChunkItem:
    chunk_index: int
    page_number: int
    page_start: int
    page_end: int
    text_content: str
    char_start: int
    char_end: int

class TextChunker:
    def __init__(self, target_chunk_chars: int = 3200, overlap_chars: int = 400):
        """
        Sensible default: ~800 tokens (~3200 chars) with ~100 tokens (~400 chars) overlap.
        Configurable for RAG retrieval and embedding generation.
        """
        self.target_chunk_chars = target_chunk_chars
        self.overlap_chars = overlap_chars

    def _split_into_paragraphs_or_sentences(self, text: str) -> List[str]:
        """Splits text along paragraph boundaries, then sentence boundaries."""
        # Split on double newline
        paragraphs = text.split("\n\n")
        units = []
        for p in paragraphs:
            p_strip = p.strip()
            if not p_strip:
                continue
            if len(p_strip) <= self.target_chunk_chars:
                units.append(p_strip)
            else:
                # Split large paragraphs by sentence boundary
                sentences = re.split(r'(?<=[.!?])\s+', p_strip)
                units.extend([s.strip() for s in sentences if s.strip()])
        return units

    def chunk_page(self, page: ExtractedPage, base_chunk_index: int) -> List[ChunkItem]:
        """
        Chunks text from a single page, ensuring exact page attribution and offsets.
        """
        text = page.normalized_text.strip()
        if not text:
            return []

        # If page text fits within target chunk size, keep it as an atomic page chunk
        if len(text) <= self.target_chunk_chars:
            return [ChunkItem(
                chunk_index=base_chunk_index,
                page_number=page.page_number,
                page_start=page.page_number,
                page_end=page.page_number,
                text_content=text,
                char_start=0,
                char_end=len(text)
            )]

        # Otherwise sliding window on sentence/paragraph boundaries
        units = self._split_into_paragraphs_or_sentences(text)
        chunks: List[ChunkItem] = []
        current_chunk_parts: List[str] = []
        current_len = 0
        current_start_offset = 0
        chunk_idx = base_chunk_index

        for unit in units:
            unit_len = len(unit)
            if current_len + unit_len + 2 > self.target_chunk_chars and current_chunk_parts:
                # Flush current chunk
                chunk_text = "\n\n".join(current_chunk_parts)
                char_end = current_start_offset + len(chunk_text)
                chunks.append(ChunkItem(
                    chunk_index=chunk_idx,
                    page_number=page.page_number,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    text_content=chunk_text,
                    char_start=current_start_offset,
                    char_end=char_end
                ))
                chunk_idx += 1

                # Calculate overlap: retain tail unit(s) if within overlap budget
                overlap_parts: List[str] = []
                overlap_acc = 0
                for part in reversed(current_chunk_parts):
                    if overlap_acc + len(part) <= self.overlap_chars:
                        overlap_parts.insert(0, part)
                        overlap_acc += len(part) + 2
                    else:
                        break

                current_start_offset = char_end - overlap_acc
                current_chunk_parts = overlap_parts + [unit]
                current_len = sum(len(p) + 2 for p in current_chunk_parts)
            else:
                current_chunk_parts.append(unit)
                current_len += unit_len + 2

        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            char_end = current_start_offset + len(chunk_text)
            chunks.append(ChunkItem(
                chunk_index=chunk_idx,
                page_number=page.page_number,
                page_start=page.page_number,
                page_end=page.page_number,
                text_content=chunk_text,
                char_start=current_start_offset,
                char_end=char_end
            ))

        return chunks

    def chunk_document(self, parsed_doc: ParsedDocument) -> List[ChunkItem]:
        """Chunks all pages of a parsed document, assigning monotonic chunk indexes."""
        all_chunks: List[ChunkItem] = []
        current_index = 0

        for page in parsed_doc.pages:
            if not page.normalized_text.strip():
                continue
            page_chunks = self.chunk_page(page, base_chunk_index=current_index)
            all_chunks.extend(page_chunks)
            current_index += len(page_chunks)

        return all_chunks

Tuple_List = List[ChunkItem]
default_chunker = TextChunker()
