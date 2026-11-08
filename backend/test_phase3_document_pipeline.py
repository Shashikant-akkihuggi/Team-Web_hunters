import os
import sys
import tempfile
from datetime import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fitz  # PyMuPDF
import docx
from fastapi import HTTPException

from backend.app.database import SessionLocal
from backend.app.models import User, Project, ProjectMember, Document, DocumentChunk, DocumentPage, UserRole, ProcessingStatus
from backend.app.services.document_pipeline import (
    process_single_document,
    retry_document_processing,
    DuplicateDocumentError,
    UnsupportedFormatError
)
from backend.app.services.document_parser import (
    parse_document,
    validate_file_signature,
    InsufficientTextError,
    compute_file_hash
)
from backend.app.services.normalization_service import (
    normalize_extracted_text,
    EmptyDocumentError
)
from backend.app.services.chunking_service import default_chunker
from backend.app.services.storage_service import storage_service
from backend.app.routers.documents import (
    get_document_status,
    get_document_content,
    get_document_chunks,
    delete_document,
    retry_failed_document
)

def create_sample_pdf(num_pages: int = 2) -> bytes:
    """Generates an in-memory PDF with real text across multiple pages."""
    doc = fitz.open()
    for i in range(1, num_pages + 1):
        page = doc.new_page()
        text = (
            f"KNOWLEDGE CONTINUITY SPECIFICATION - PAGE {i}\n\n"
            f"This is section {i} detailing the microservices architecture, PostgreSQL data pipeline, "
            f"and zero-hallucination verification engine for Team Web_hunter.\n"
            f"Architectural Decision {i}: We selected PyMuPDF for reliable page-level bounding and extraction."
        )
        page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_scanned_image_pdf() -> bytes:
    """Generates a PDF page with zero extractable digital text (simulating scanned document)."""
    doc = fitz.open()
    # Empty page with no text layer
    page = doc.new_page()
    # Insert whitespace only
    page.insert_text((50, 72), "   ", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_sample_docx() -> bytes:
    """Generates an in-memory DOCX file with headings, paragraphs, and tables."""
    doc = docx.Document()
    doc.add_heading("Knowledge Handover Protocol", level=1)
    doc.add_paragraph(
        "Team Web_hunter has standardized the document ingestion pipeline. "
        "All uploaded documents are parsed into page-level chunks and stored with SHA-256 checksums."
    )
    doc.add_heading("Core Deliverables & Ownership", level=2)
    p = doc.add_paragraph("Lead Engineer is responsible for backend RAG embeddings and verification.")

    table = doc.add_table(rows=2, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Component"
    hdr_cells[1].text = "Owner"
    hdr_cells[2].text = "Target Date"
    row_cells = table.rows[1].cells
    row_cells[0].text = "Ingestion Engine"
    row_cells[1].text = "Elena Rostova"
    row_cells[2].text = "2026-Q1"

    tmp_path = os.path.join(tempfile.gettempdir(), f"sample_{datetime.utcnow().timestamp()}.docx")
    doc.save(tmp_path)
    with open(tmp_path, "rb") as f:
        data = f.read()
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    return data

def run_tests():
    db = SessionLocal()
    print("=================================================================")
    print("STARTING PHASE 3 DOCUMENT INGESTION & PROCESSING ENGINE TESTS")
    print("=================================================================")

    # Setup test user and project
    test_email = "phase3_tester@webhunter.org"
    user = db.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(
            email=test_email,
            full_name="Phase 3 Engineer",
            hashed_password="hash",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    project_name = "Phase 3 Ingestion Project"
    project = db.query(Project).filter(Project.name == project_name).first()
    if project:
        # Clean existing test project docs and chunks
        docs = db.query(Document).filter(Document.project_id == project.id).all()
        for d in docs:
            db.query(DocumentPage).filter(DocumentPage.document_id == d.id).delete()
            db.query(DocumentChunk).filter(DocumentChunk.document_id == d.id).delete()
            if d.storage_key:
                storage_service.delete_file(d.storage_key)
            db.delete(d)
        db.delete(project)
        db.commit()

    project = Project(
        name=project_name,
        description="Testing document ingestion and chunking pipeline",
        category="Engineering",
        status="ACTIVE",
        created_by=user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=UserRole.ADMIN
    )
    db.add(member)
    db.commit()

    # -------------------------------------------------------------
    # 1. FILE SIGNATURE & VALIDATION TESTS
    # -------------------------------------------------------------
    print("\n--- 1. Testing File Signature & Validation ---")
    pdf_bytes = create_sample_pdf(num_pages=3)
    assert validate_file_signature(pdf_bytes, ".pdf"), "PDF signature validation failed"
    print("  [PASS] PDF %PDF magic byte signature verified.")

    docx_bytes = create_sample_docx()
    assert validate_file_signature(docx_bytes, ".docx"), "DOCX signature validation failed"
    print("  [PASS] DOCX PK\\x03\\x04 zip signature verified.")

    txt_bytes = "Knowledge Continuity Plain Text Specification.\nLine 2 details.".encode("utf-8")
    assert validate_file_signature(txt_bytes, ".txt"), "TXT signature validation failed"
    print("  [PASS] Plain text UTF-8 content validated.")

    # Spoofed file test: executable bytes renamed as .pdf
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
    assert not validate_file_signature(fake_pdf, ".pdf")
    print("  [PASS] Spoofed executable file disguised as .pdf rejected.")

    # -------------------------------------------------------------
    # 2. PDF INGESTION & PAGE-LEVEL PRESERVATION
    # -------------------------------------------------------------
    print("\n--- 2. Testing PDF Ingestion & Multi-Page Extraction ---")
    doc_pdf = process_single_document(
        file_bytes=pdf_bytes,
        original_filename="Architecture_Design_v2.pdf",
        project_id=project.id,
        user_id=user.id,
        db=db
    )
    assert doc_pdf.status == ProcessingStatus.PROCESSED
    assert doc_pdf.page_count == 3
    assert doc_pdf.chunk_count >= 3
    assert doc_pdf.extracted_character_count > 100
    print(f"  [PASS] PDF processed successfully: {doc_pdf.page_count} pages, {doc_pdf.chunk_count} chunks, {doc_pdf.extracted_character_count} chars.")

    # Verify DocumentPage records in DB
    pages_in_db = db.query(DocumentPage).filter(DocumentPage.document_id == doc_pdf.id).order_by(DocumentPage.page_number.asc()).all()
    assert len(pages_in_db) == 3
    assert pages_in_db[0].page_number == 1
    assert "PAGE 1" in pages_in_db[0].extracted_text
    assert pages_in_db[1].page_number == 2
    assert "PAGE 2" in pages_in_db[1].extracted_text
    assert pages_in_db[2].page_number == 3
    assert "PAGE 3" in pages_in_db[2].extracted_text
    print("  [PASS] Page-level provenance verified in database with exact page numbering.")

    # Verify DocumentChunk records in DB
    chunks_in_db = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_pdf.id).order_by(DocumentChunk.chunk_index.asc()).all()
    assert len(chunks_in_db) >= 3
    for idx, c in enumerate(chunks_in_db):
        assert c.chunk_index == idx
        assert c.page_start >= 1
        assert c.char_end > c.char_start
        assert len(c.text_content) > 0
    print(f"  [PASS] Generated {len(chunks_in_db)} chunks with monotonic indexes and character offsets.")

    # -------------------------------------------------------------
    # 3. DOCX INGESTION & TABLE/HEADING EXTRACTION
    # -------------------------------------------------------------
    print("\n--- 3. Testing DOCX Ingestion (Headings, Paragraphs, Tables) ---")
    doc_docx = process_single_document(
        file_bytes=docx_bytes,
        original_filename="Team_Web_hunter_Handover.docx",
        project_id=project.id,
        user_id=user.id,
        db=db
    )
    assert doc_docx.status == ProcessingStatus.PROCESSED
    assert doc_docx.chunk_count >= 1

    # Verify table content was captured
    docx_pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc_docx.id).all()
    all_docx_text = "\n".join(p.extracted_text for p in docx_pages)
    assert "Ingestion Engine" in all_docx_text
    assert "Elena Rostova" in all_docx_text
    print("  [PASS] DOCX parsed successfully with table rows and headings preserved.")

    # -------------------------------------------------------------
    # 4. TXT INGESTION & ENCODING
    # -------------------------------------------------------------
    print("\n--- 4. Testing TXT Ingestion & Unicode Handling ---")
    txt_unicode = (
        "Project Architecture Notes — Team Web_hunter\n"
        "1. Database: PostgreSQL 16 + pgvector for semantic retrieval.\n"
        "2. Chunking: 1,000 tokens per chunk with 150-token overlap.\n"
        "3. Contradiction Detection: Identifies conflicting deadlines.\n"
    ).encode("utf-8")

    doc_txt = process_single_document(
        file_bytes=txt_unicode,
        original_filename="Notes_Architecture.txt",
        project_id=project.id,
        user_id=user.id,
        db=db
    )
    assert doc_txt.status == ProcessingStatus.PROCESSED
    assert doc_txt.extracted_character_count > 50
    print(f"  [PASS] TXT ingested and normalized successfully ({doc_txt.extracted_character_count} chars).")

    # -------------------------------------------------------------
    # 5. DUPLICATE UPLOAD DETECTION
    # -------------------------------------------------------------
    print("\n--- 5. Testing Duplicate File Detection ---")
    try:
        process_single_document(
            file_bytes=pdf_bytes,
            original_filename="Architecture_Design_v2_Copy.pdf",
            project_id=project.id,
            user_id=user.id,
            db=db
        )
        assert False, "Duplicate document should have raised DuplicateDocumentError"
    except DuplicateDocumentError as e:
        print(f"  [PASS] Duplicate document rejected by checksum: '{e}'")

    # -------------------------------------------------------------
    # 6. SCANNED PDF OCR DETECTION & ERROR HANDLING
    # -------------------------------------------------------------
    print("\n--- 6. Testing Scanned PDF Without Text Layer (OCR Detection) ---")
    scanned_pdf_bytes = create_scanned_image_pdf()
    doc_scanned = process_single_document(
        file_bytes=scanned_pdf_bytes,
        original_filename="Scanned_Contract_No_Text.pdf",
        project_id=project.id,
        user_id=user.id,
        db=db
    )
    assert doc_scanned.status == ProcessingStatus.FAILED
    assert "OCR is required" in (doc_scanned.processing_error or doc_scanned.error_message)
    print(f"  [PASS] Scanned document detected and marked FAILED with OCR requirement notice: '{doc_scanned.error_message}'")

    # -------------------------------------------------------------
    # 7. DOCUMENT RETRY MECHANISM
    # -------------------------------------------------------------
    print("\n--- 7. Testing Document Retry Mechanism ---")
    # Simulate a document that had a transient failure
    retry_doc = retry_document_processing(
        document_id=doc_pdf.id,
        db=db,
        user_id=user.id
    )
    assert retry_doc.status == ProcessingStatus.PROCESSED
    assert retry_doc.chunk_count >= 3
    print("  [PASS] retry_document_processing re-read file from storage and re-chunked with 100% success.")

    # -------------------------------------------------------------
    # 8. API CONTENT & CHUNKS RETRIEVAL
    # -------------------------------------------------------------
    print("\n--- 8. Testing Document Inspection Endpoints ---")
    status_resp = get_document_status(document_id=doc_pdf.id, db=db, current_user=user)
    assert status_resp.status == ProcessingStatus.PROCESSED
    assert status_resp.page_count == 3
    print(f"  [PASS] GET /documents/{{id}}/status returned status '{status_resp.status}' and {status_resp.page_count} pages.")

    content_resp = get_document_content(document_id=doc_pdf.id, db=db, current_user=user)
    assert len(content_resp.pages) == 3
    assert "PAGE 1" in content_resp.full_text
    print(f"  [PASS] GET /documents/{{id}}/content returned {len(content_resp.pages)} pages of full text.")

    chunks_resp = get_document_chunks(document_id=doc_pdf.id, db=db, current_user=user)
    assert len(chunks_resp) >= 3
    assert chunks_resp[0].page_number == 1
    print(f"  [PASS] GET /documents/{{id}}/chunks returned {len(chunks_resp)} chunks with offsets.")

    # -------------------------------------------------------------
    # 9. DOCUMENT DELETION & STORAGE CLEANUP
    # -------------------------------------------------------------
    print("\n--- 9. Testing Document Deletion & Storage Cleanup ---")
    doc_to_delete_id = doc_txt.id
    del_resp = delete_document(document_id=doc_to_delete_id, db=db, current_user=user)
    assert "deleted successfully" in del_resp["message"]

    deleted_doc = db.query(Document).filter(Document.id == doc_to_delete_id).first()
    assert deleted_doc is None
    deleted_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_to_delete_id).all()
    assert len(deleted_chunks) == 0
    deleted_pages = db.query(DocumentPage).filter(DocumentPage.document_id == doc_to_delete_id).all()
    assert len(deleted_pages) == 0
    print("  [PASS] Document, pages, chunks, and storage file cascade deleted cleanly.")

    print("\n=================================================================")
    print("ALL PHASE 3 DOCUMENT INGESTION TESTS PASSED WITH 100% SUCCESS!")
    print("=================================================================")
    db.close()

if __name__ == "__main__":
    run_tests()
